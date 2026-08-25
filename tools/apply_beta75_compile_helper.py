#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
s=p.read_text(encoding='utf-8')
anchor='    private fun activeAssignments(s:JSONObject,type:String=""):List<JSONObject>{'
helper='    private fun activePositions(s:JSONObject):List<JSONObject>{val out=mutableListOf<JSONObject>();val a=positionArray(s);for(i in 0 until a.length()){val x=a.optJSONObject(i)?:continue;if(x.optString("state").equals("ACTIVE",true))out.add(x)};return out}\n'
if helper.strip() not in s:
    if s.count(anchor)!=1: raise SystemExit('activeAssignments anchor drift')
    s=s.replace(anchor,helper+anchor,1)
p.write_text(s,encoding='utf-8')
print('Beta75 activePositions helper applied')
