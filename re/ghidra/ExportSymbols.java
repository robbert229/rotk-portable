// Export new function entry points as symdb auto candidates.
//@category ROTK

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;
import java.util.TreeMap;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.symbol.SourceType;

public class ExportSymbols extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (!Files.isRegularFile(Path.of(args[3]))) {
            throw new IllegalStateException("Symbol import did not complete");
        }
        var ranges = new TreeMap<Long, Long>();
        try (var reader = Files.newBufferedReader(Path.of(args[0]))) {
            reader.readLine();
            String line;
            while ((line = reader.readLine()) != null) {
                String[] fields = line.split(",", 3);
                long start = Long.decode(fields[0]);
                ranges.put(start, start + Math.max(1, Long.decode(fields[1])));
            }
        }
        int exported = 0;
        try (var writer = Files.newBufferedWriter(Path.of(args[1]))) {
            writer.write("address,size,name,unit,module,kind,signature,status,evidence\n");
            for (var function : currentProgram.getFunctionManager().getFunctions(true)) {
                monitor.checkCancelled();
                if (function.getSymbol().getSource() == SourceType.USER_DEFINED) {
                    continue;
                }
                var entry = function.getEntryPoint();
                long va = entry.getOffset();
                if (!entry.getAddressSpace().equals(currentProgram.getImageBase().getAddressSpace())
                        || va < 0x400000 || va > 0xffffffffL) {
                    continue;
                }
                var range = ranges.floorEntry(va);
                if (range != null && va < range.getValue()) {
                    continue;
                }
                String hex = String.format(Locale.ROOT, "%08X", va);
                writer.write("0x" + hex + ",0x0,FUN_" + hex + ",," + args[2] + ",func,,auto,\n");
                exported++;
            }
        }
        println("Auto rows exported: " + exported);
    }
}
