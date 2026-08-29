import fs from "node:fs";
const m=JSON.parse(fs.readFileSync("qa/chaos_matrix.json","utf8"));
if(m.required_cases!==33||m.cases.length!==33)throw new Error("CHAOS_CASE_COUNT");
const ids=m.cases.map(x=>x.id);if(new Set(ids).size!==33||Math.min(...ids)!==1||Math.max(...ids)!==33)throw new Error("CHAOS_IDS");
const allowed=new Set(["AUTOMATED","LIVE_SERVICE","LIVE_GAS","EMULATOR","TEMP_LIVE_D1","LIVE_DR","REAL_3_PDA_8H","EXACT_CANDIDATE"]);
for(const c of m.cases){if(!c.name||!c.gate||!allowed.has(c.requires))throw new Error("CHAOS_CASE_INVALID_"+c.id);}
console.log("chaos_matrix_contract=PASS cases=33 hardware_case=29");
