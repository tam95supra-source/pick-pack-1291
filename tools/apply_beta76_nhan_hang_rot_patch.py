#!/usr/bin/env python3
from pathlib import Path

OPS=Path('app/src/main/java/vn/pickpack1291/app/beta/OperationsActivity.kt')
GAS=Path('google-apps-script/PICK_PACK_API.gs')

ops=OPS.read_text(encoding='utf-8')
old_card='businessCard(R.drawable.ic_pp_drop_receive,"Nhận hàng Rớt","",true){TopNotice.show(this,"Nhận hàng Rớt đang được chuẩn bị.",TopNotice.Kind.INFO)}'
new_card='businessCard(R.drawable.ic_pp_drop_receive,"Nhận hàng Rớt","",true){dropReceiveScreen()}'
if old_card in ops:
    assert ops.count(old_card)==1, 'drop receive card anchor drift'
    ops=ops.replace(old_card,new_card,1)
elif new_card not in ops:
    raise SystemExit('drop receive card anchor missing')

fn='''\n    private fun dropReceiveScreen(){\n        module="BUSINESS"\n        screenState="DROP_RECEIVE"\n        setScreen(DropReceiveFeature.build(this,api,login,name,role){businessHome()})\n    }\n\n'''
anchor='    // S61_BETA60_SHIFT_RECONCILIATION_ACTIONS: exact counts + direct employee RA entry.\n'
if 'private fun dropReceiveScreen()' not in ops:
    assert ops.count(anchor)==1, 'drop receive function anchor drift'
    ops=ops.replace(anchor,fn+anchor,1)

old_back='"SCAN","LABOR_HOME","RESOURCE_HOME","REPORT","LISTS","PDA_EXCHANGE"->businessHome()'
new_back='"SCAN","LABOR_HOME","RESOURCE_HOME","REPORT","LISTS","PDA_EXCHANGE","DROP_RECEIVE"->businessHome()'
if old_back in ops:
    assert ops.count(old_back)==1, 'navigateBack anchor drift'
    ops=ops.replace(old_back,new_back,1)
elif new_back not in ops:
    raise SystemExit('navigateBack anchor missing')
OPS.write_text(ops,encoding='utf-8')

gas=GAS.read_text(encoding='utf-8')
route_block='''    if (action === 'outbound_location_list') return ppJson_(ppOutboundLocationList_(auth));\n    if (action === 'outbound_location_mutate') return ppJson_(ppWithLock_(function(){ return ppOutboundLocationMutate_(auth, body); }));\n    if (action === 'outbound_drop_append') return ppJson_(ppWithLock_(function(){ return ppOutboundAppend_(auth, body); }));\n    if (action === 'outbound_drop_clear') return ppJson_(ppWithLock_(function(){ return ppOutboundClear_(auth, body); }));\n'''
if "action === 'outbound_drop_append'" not in gas:
    route_anchor="    if (action === 'sync_status') return ppJson_(ppSyncStatus_());\n"
    assert gas.count(route_anchor)==1, 'GAS outbound route anchor drift'
    gas=gas.replace(route_anchor,route_anchor+route_block,1)
for required in ('ppOutboundLocationList_(auth)','ppOutboundLocationMutate_(auth, body)','ppOutboundAppend_(auth, body)','ppOutboundClear_(auth, body)'):
    assert required in gas, required
GAS.write_text(gas,encoding='utf-8')

print('beta76_nhan_hang_rot_patch=PASS')
