#!/usr/bin/env python3
from pathlib import Path
import re

p=Path(__file__).resolve().parents[1]/'app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt'
s=p.read_text()

# Legacy merge blocks must never survive Beta64. Used users are selected only through
# the dedicated reissue chooser and are not appended to the normal unused list.
s=re.sub(r'\s*if\(allowPickReissue\)\{val used=mutableListOf<String>\(\);for\(i in 0 until pickReissue\.length\(\)\)\{val id=pickReissue\.optJSONObject\(i\)\?\.optString\("id"\)\.orEmpty\(\)\.trim\(\);if\(id\.isNotBlank\(\)&&!base\.contains\(id\)&&!used\.contains\(id\)\)used\.add\(id\)\};sortedByNaturalUser\(used\)\{it\}\.forEach\{pickChoices\.add\(it to true\);labels\.add\("⚠ \\$it • ĐÃ DÙNG HÔM NAY"\)\}\}', '', s)
s=s.replace(';if(allowPackReissue)addPack(packReissue,true)','')
s=s.replace(';if(allowPackReissue)addRows(packReissue,true)','')

# Replace any residual legacy Pick reissue button, in either editor or enter screen.
legacy_pick_resources='compactReissueButton("Phát lại user pick",pickReissue.length()>0&&!allowPickReissue){allowPickReissue=true;rebuildResources?.invoke()}'
new_pick_resources='compactReissueButton("Phát lại user pick",pickReissue.length()>0){val used=mutableListOf<String>();for(i in 0 until pickReissue.length()){val id=pickReissue.optJSONObject(i)?.optString("id").orEmpty().trim();if(id.isNotBlank()&&!used.contains(id))used.add(id)};val sorted=sortedByNaturalUser(used){it};showReissueChooser("Chọn User Pick đã dùng",sorted){idx->selectedPickReissue=sorted[idx];TopNotice.show(this,"Đã chọn phát lại ${sorted[idx]}",TopNotice.Kind.INFO)}}'
s=s.replace(legacy_pick_resources,new_pick_resources)
legacy_pick_editor='compactReissueButton("Phát lại user pick",pickReissue.length()>0&&!allowPickReissue){allowPickReissue=true;rebuild()}'
new_pick_editor='compactReissueButton("Phát lại user pick",pickReissue.length()>0){val used=mutableListOf<String>();for(i in 0 until pickReissue.length()){val id=pickReissue.optJSONObject(i)?.optString("id").orEmpty().trim();if(id.isNotBlank()&&!used.contains(id))used.add(id)};val sorted=sortedByNaturalUser(used){it};showReissueChooser("Chọn User Pick đã dùng",sorted){idx->selectedPickReissue=sorted[idx];TopNotice.show(this,"Đã chọn phát lại ${sorted[idx]}",TopNotice.Kind.INFO)}}'
s=s.replace(legacy_pick_editor,new_pick_editor)

# Replace any residual legacy Pack reissue button.
legacy_pack_resources='compactReissueButton("Phát lại user pack",packReissue.length()>0&&!allowPackReissue){allowPackReissue=true;rebuildResources?.invoke()}'
new_pack_resources='compactReissueButton("Phát lại user pack",packReissue.length()>0){val used=mutableListOf<JSONObject>();for(i in 0 until packReissue.length()){val o=packReissue.optJSONObject(i)?:continue;if(o.optString("table").isNotBlank()&&o.optString("user_pack").isNotBlank())used.add(JSONObject(o.toString()).put("duplicate_user",true))};val labels=used.map{"${it.optString("table")} • ${it.optString("user_pack")}"};showReissueChooser("Chọn User Pack đã dùng",labels){idx->selectedPackReissue=used[idx];TopNotice.show(this,"Đã chọn phát lại ${labels[idx]}",TopNotice.Kind.INFO)}}'
s=s.replace(legacy_pack_resources,new_pack_resources)
legacy_pack_editor='compactReissueButton("Phát lại user pack",packReissue.length()>0&&!allowPackReissue){allowPackReissue=true;rebuild()}'
new_pack_editor='compactReissueButton("Phát lại user pack",packReissue.length()>0){val used=mutableListOf<JSONObject>();for(i in 0 until packReissue.length()){val o=packReissue.optJSONObject(i)?:continue;if(o.optString("table").isNotBlank()&&o.optString("user_pack").isNotBlank())used.add(JSONObject(o.toString()).put("duplicate_user",true))};val labels=used.map{"${it.optString("table")} • ${it.optString("user_pack")}"};showReissueChooser("Chọn User Pack đã dùng",labels){idx->selectedPackReissue=used[idx];TopNotice.show(this,"Đã chọn phát lại ${labels[idx]}",TopNotice.Kind.INFO)}}'
s=s.replace(legacy_pack_editor,new_pack_editor)

# Remove now-obsolete toggle declarations if they survived.
s=s.replace('var allowPickReissue=false;var allowPackReissue=false','')

if 'allowPickReissue' in s or 'allowPackReissue' in s:
    raise SystemExit('residual legacy reissue toggle remains')
if 'Chọn User Pick đã dùng' not in s or 'Chọn User Pack đã dùng' not in s:
    raise SystemExit('dedicated reissue chooser missing')
p.write_text(s)
print('Beta64 residual reissue compile fix PASS')
