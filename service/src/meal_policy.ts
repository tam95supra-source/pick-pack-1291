export type MealPolicyRow={
  mnv?:unknown;
  shift?:unknown;
  status?:unknown;
  expected_return_at?:unknown;
  actual_return_at?:unknown;
};

function timeMs(v:unknown):number{return Date.parse(String(v??""))||0;}

export function mealStatusView(row:MealPolicyRow,nowMs:number):string{
  const status=String(row.status??"PENDING");
  if(status==="LATE_EXPECTED"){
    const expected=timeMs(row.expected_return_at);
    if(expected>0&&nowMs>=expected&&!row.actual_return_at)return "OVERDUE_LATE";
  }
  return status;
}

export function mealAlert(rows:Array<MealPolicyRow&{status_view?:unknown}>,minutes:number,nowMs:number){
  const eligible=new Set<string>();
  if(minutes>=12*60){eligible.add("Ca 1");eligible.add("Ca HC");}
  if(minutes>=19*60)eligible.add("Ca 2");
  const unresolved=rows
    .map(x=>({...x,status_view:String(x.status_view||mealStatusView(x,nowMs))}))
    .filter(x=>eligible.has(String(x.shift??""))&&(x.status_view==="PENDING"||x.status_view==="OVERDUE_LATE"));
  let severity:"NONE"|"WARNING"|"SEVERE"="NONE";
  if(unresolved.length){
    const severe=unresolved.some(x=>x.status_view==="OVERDUE_LATE"||
      ((String(x.shift??"")==="Ca 1"||String(x.shift??"")==="Ca HC")&&minutes>=12*60+30)||
      (String(x.shift??"")==="Ca 2"&&minutes>=19*60+30));
    severity=severe?"SEVERE":"WARNING";
  }
  return{severity,unresolved_count:unresolved.length,unresolved_mnvs:unresolved.map(x=>String(x.mnv??"")).filter(Boolean).slice(0,50)};
}
