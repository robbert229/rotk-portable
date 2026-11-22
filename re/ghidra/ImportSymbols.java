// Apply the symdb export-ghidra CSV to the analyzed program.
//@category ROTK

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;
import java.util.HashSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import ghidra.app.cmd.function.ApplyFunctionSignatureCmd;
import ghidra.app.script.GhidraScript;
import ghidra.app.services.DataTypeManagerService;
import ghidra.app.util.cparser.C.CParser;
import ghidra.app.util.cparser.C.CParserUtils;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.data.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;

public class ImportSymbols extends GhidraScript {
    private static final Pattern FIELD = Pattern.compile("\"((?:[^\"]|\"\")*)\"|([^,\"]*)");

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (!args[2].equalsIgnoreCase(currentProgram.getExecutableSHA256())) {
            throw new IllegalArgumentException("Executable hash mismatch; use --reimport");
        }
        Set<String> auto = new HashSet<>(Files.readAllLines(Path.of(args[1])));
        int applied = 0;
        int conflicts = 0;
        try (var reader = Files.newBufferedReader(Path.of(args[0]))) {
            if (!"address,size,name,kind,signature".equals(reader.readLine())) {
                throw new IllegalArgumentException("Expected symdb export-ghidra header");
            }
            String line;
            while ((line = reader.readLine()) != null) {
                monitor.checkCancelled();
                String[] row = parseRow(line);
                try {
                    apply(row, auto.contains(row[0].substring(2)));
                    applied++;
                }
                catch (Exception error) {
                    conflicts++;
                    println("Conflict " + row[0] + " " + row[2] + ": " + error.getMessage());
                }
            }
        }
        int functions = 0;
        for (var iterator = currentProgram.getFunctionManager().getFunctions(true);
                iterator.hasNext(); ) {
            iterator.next();
            functions++;
        }
        Files.writeString(Path.of(args[3]), String.format(
            "Functions: %d, symbols applied: %d, conflicts: %d%n", functions, applied, conflicts));
    }

    private String[] parseRow(String line) {
        String[] row = new String[5];
        Matcher matcher = FIELD.matcher(line);
        int position = 0;
        for (int i = 0; i < row.length; i++) {
            matcher.region(position, line.length());
            if (!matcher.lookingAt()) {
                throw new IllegalArgumentException("Invalid CSV field");
            }
            row[i] = matcher.group(1) == null ? matcher.group(2) :
                matcher.group(1).replace("\"\"", "\"");
            position = matcher.end();
            if (i < row.length - 1 && (position >= line.length() || line.charAt(position++) != ',')) {
                throw new IllegalArgumentException("Missing CSV separator");
            }
        }
        if (position != line.length()) {
            throw new IllegalArgumentException("Unexpected CSV suffix");
        }
        return row;
    }

    private void apply(String[] row, boolean auto) throws Exception {
        Address address = toAddr(Long.decode(row[0]));
        long size = Long.decode(row[1]);
        String name = row[2];
        String signature = row[4];
        Address end = address.addNoWrap(Math.max(size, 1) - 1);
        if (!currentProgram.getMemory().contains(address, end)) {
            throw new IllegalArgumentException("range is outside program memory");
        }
        var table = currentProgram.getSymbolTable();
        Symbol primary = table.getPrimarySymbol(address);
        for (Symbol symbol : table.getSymbols(address)) {
            if (auto && symbol.getSource() == SourceType.USER_DEFINED) {
                throw new IllegalArgumentException("would replace user-defined symbol " + symbol.getName());
            }
        }
        SourceType source = auto ? SourceType.ANALYSIS : SourceType.USER_DEFINED;
        if (row[3].equals("func") || row[3].equals("lib")) {
            applyFunction(address, size, end, name, signature, source);
        }
        else {
            if (getFunctionAt(address) != null || getInstructionContaining(address) != null) {
                throw new IllegalArgumentException("data label is on code");
            }
            applyData(address, size, name, signature);
            if (primary == null || !primary.getName().equals(name)) {
                Symbol label = createLabel(address, name, true, source);
                if (!label.isPrimary()) {
                    throw new IllegalArgumentException("could not set primary label");
                }
            }
        }
    }

    private void applyFunction(Address address, long size, Address end, String name,
            String signature, SourceType source) throws Exception {
        var definition = signature.isEmpty() ? null :
            CParserUtils.parseSignature((DataTypeManagerService) null, currentProgram, signature, false);
        if (!signature.isEmpty() && (definition == null || !definition.getName().equals(name))) {
            throw new IllegalArgumentException("invalid or mismatched function declaration");
        }
        Function function = getFunctionAt(address);
        if (size != 0) {
            AddressSet body = new AddressSet(address, end);
            Instruction first = getInstructionContaining(address);
            Instruction last = getInstructionContaining(end);
            if ((first != null && !first.getMinAddress().equals(address)) ||
                    (last != null && !last.getMaxAddress().equals(end))) {
                throw new IllegalArgumentException("function range cuts an instruction");
            }
            if (function == null) {
                function = currentProgram.getListing().createFunction(name, address, body, source);
            }
            else if (!function.getBody().hasSameAddresses(body)) {
                function.setBody(body);
            }
        }
        else if (function == null) {
            if (getInstructionAt(address) == null && !disassemble(address)) {
                throw new IllegalArgumentException("could not disassemble function entry");
            }
            function = createFunction(address, null);
        }
        if (function == null) {
            throw new IllegalArgumentException("could not create function");
        }
        if (definition != null) {
            var command = new ApplyFunctionSignatureCmd(address, definition, source, false, false);
            if (!command.applyTo(currentProgram, monitor)) {
                throw new IllegalArgumentException(command.getStatusMsg());
            }
        }
        if (!function.getName().equals(name) ||
                (source == SourceType.USER_DEFINED && function.getSymbol().getSource() != source)) {
            function.setName(name, source);
        }
    }

    private void applyData(Address address, long size, String name, String signature)
            throws Exception {
        if (size == 0 && signature.isEmpty()) {
            return;
        }
        DataType type;
        if (signature.isEmpty()) {
            type = new ArrayDataType(Undefined1DataType.dataType, Math.toIntExact(size), 1);
        }
        else {
            String alias = "__rotk_import_type";
            String declaration = signature.replaceAll("\\b" + name + "\\b", alias);
            DataType parsed = new CParser(currentProgram.getDataTypeManager(), false, null).parse(
                "typedef " + declaration + ";");
            if (!(parsed instanceof TypeDef typedef) || !parsed.getName().equals(alias)) {
                throw new IllegalArgumentException("could not resolve data declaration");
            }
            type = typedef.getDataType();
        }
        if (type.getLength() <= 0 || (size > 0 && type.getLength() != size)) {
            throw new IllegalArgumentException("data declaration and size disagree");
        }
        Data data = getDataAt(address);
        if (data != null && data.isDefined()) {
            if (!data.getDataType().isEquivalent(type) &&
                    !(signature.isEmpty() && data.getLength() == size)) {
                throw new IllegalArgumentException("existing data has a different type or size");
            }
        }
        else {
            currentProgram.getListing().createData(address, type);
        }
    }
}
