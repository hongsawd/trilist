/* Shared ordering and sync rules. No device data or credentials belong here. */
(function (root) {
  "use strict";
  const cats = {urgent:["紧急","pink",5], action:["要办","amber",3], academic:["学业","blue",3], info:["信息","gray",1]};
  let clock = 0;
  const has = (x, k) => Object.prototype.hasOwnProperty.call(x, k);
  const key = x => x.kind + "|" + x.id;
  function observe(value) { if (Number.isFinite(+value)) clock = Math.max(clock, +value); }
  function tick() { return clock = Math.max(Date.now(), clock + 1); }
  function category(x) {
    return cats[x.cat] ? x.cat : /紧急/.test(x.tag || "") ? "urgent" : /学业|课业/.test(x.tag || "") ? "academic" : /信息|通知/.test(x.tag || "") ? "info" : "action";
  }
  function todo(x, source) {
    const out = {...x, cat:category(x)};
    out.tag = cats[out.cat][0]; out.tone = cats[out.cat][1];
    // Explicit empty fields must win over old aliases after clearing an editor.
    out.place = String(source === "desktop" && has(x,"where") ? x.where : has(x,"place") ? x.place : x.where || "");
    out.where = out.place;
    out.note = String(has(x,"note") ? x.note : x.meta || "");
    out.done = !!x.done;
    out.meta = [[out.date ? out.date.slice(5) : "", out.time || ""].filter(Boolean).join(" "), out.place ? "@"+out.place : "", out.note].filter(Boolean).join(" · ");
    return out;
  }
  function event(x, source) {
    const out = {...x};
    out.place = String(source === "desktop" && has(x,"where") ? x.where : has(x,"place") ? x.place : x.where || "");
    out.where = out.place;
    out.kind = out.kind || (cats[out.cat] ? cats[out.cat][0] : "日程");
    return out;
  }
  function compareTodos(a,b) {
    return Number(!!a.done)-Number(!!b.done) || cats[category(b)][2]-cats[category(a)][2]
      || (a.date ? a.date+(a.time||"23:59") : "9999").localeCompare(b.date ? b.date+(b.time||"23:59") : "9999")
      || String(a.id).localeCompare(String(b.id));
  }
  function compareAgenda(a,b) {
    return Number(!!a.past)-Number(!!b.past) || String(a.date||"").localeCompare(String(b.date||""))
      || Number(!!a.courseId)-Number(!!b.courseId)
      || String(a.time||"99:99").localeCompare(String(b.time||"99:99"))
      || String(a.id||a.courseId||"").localeCompare(String(b.id||b.courseId||""));
  }
  function stable(x) {
    if (Array.isArray(x)) return "["+x.map(stable).join(",")+"]";
    if (x && typeof x === "object") return "{"+Object.keys(x).sort().filter(k=>x[k]!==undefined).map(k=>JSON.stringify(k)+":"+stable(x[k])).join(",")+"}";
    return JSON.stringify(x);
  }
  function valid(x) {
    return x && ["todo","event","thought","course"].includes(x.kind) && typeof x.id === "string"
      && x.id.length > 0 && Number.isFinite(+x.updatedAt) && +x.updatedAt > 0
      && (x.deleted === true || (x.payload && typeof x.payload === "object" && !Array.isArray(x.payload)));
  }
  function snapshot(data) {
    if (!data || data.ok !== true || !Array.isArray(data.items) || !data.items.every(valid)) throw new Error("同步响应不完整，已保留本机数据");
    data.items.forEach(x=>observe(x.updatedAt));
    return data.items;
  }
  function merge(local, remote) {
    const items = new Map();
    for (const x of [...local,...remote]) {
      if (!valid(x)) continue;
      observe(x.updatedAt);
      const old = items.get(key(x));
      if (!old || +x.updatedAt > +old.updatedAt || (+x.updatedAt === +old.updatedAt && (!old.deleted || x.deleted))) items.set(key(x),x);
    }
    return [...items.values()].sort((a,b)=>key(a).localeCompare(key(b)));
  }
  function viewVersion(row) {
    if (row.deleted) return {kind:row.kind,id:row.id,updatedAt:row.updatedAt,deleted:true};
    const x=row.kind==="todo"?todo(row.payload):row.kind==="event"?event(row.payload):row.payload;
    const fields={todo:["text","cat","date","time","place","note","done","doneAt"],event:["text","date","time","endDate","endTime","place","kind","note","done","doneAt"],thought:["text"],course:["name","day","start","end","weeks","place","teacher","classNo","color"]}[row.kind];
    const payload={};
    fields.forEach(k=>payload[k]=k==="done"?!!x[k]:x[k]??"");
    return {kind:row.kind,id:row.id,updatedAt:row.updatedAt,payload};
  }
  function equal(a,b) { return stable(merge([],a).map(viewVersion)) === stable(merge([],b).map(viewVersion)); }
  function ledger() {
    let account = "", versions = new Map();
    const version = x => String(x.updatedAt) + "|" + !!x.deleted;
    return {
      use(identity) { if (identity !== account) { account=identity; versions.clear(); } },
      pending(items) { return items.filter(x=>versions.get(key(x))!==version(x)); },
      acknowledge(items) { items.forEach(x=>versions.set(key(x),version(x))); }
    };
  }
  function firstMerge(local, remote) {
    const cloud = new Map(remote.map(x=>[key(x),x]));
    const kept = local.map(x=>{
      const other = cloud.get(key(x));
      if (!other || x.deleted) return x;
      const withoutVersion = row => {
        const out = {...row.payload}; delete out.updatedAt;
        return out;
      };
      if (!other.deleted && stable(withoutVersion(x)) === stable(withoutVersion(other))) return other;
      const id = "local-" + crypto.randomUUID();
      return {...x,id,updatedAt:tick(),payload:{...x.payload,id}};
    });
    return merge(kept, remote);
  }
  root.SangeCore = {tick,observe,category,todo,event,compareTodos,compareAgenda,stable,key,snapshot,merge,equal,ledger,firstMerge};
})(typeof globalThis !== "undefined" ? globalThis : window);
