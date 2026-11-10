"use strict";
function leadMinutes(value) {
  if (value === null) return null;
  const minutes=Number(value === undefined ? 30 : value);
  return Number.isInteger(minutes) && minutes>=0 && minutes<=10080 ? minutes : 30;
}
function isDue(item,now=Date.now()) {
  const minutes=leadMinutes(item.remindBefore);
  if (minutes===null) return false;
  const start=new Date(item.startAt).getTime();
  return Number.isFinite(start) && now>=start-minutes*60000 && now<=start+2*60000;
}
module.exports={leadMinutes,isDue};
