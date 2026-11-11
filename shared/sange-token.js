/* Shared user-facing token creation and copying. Credentials stay on the device. */
(function(root){
  "use strict";
  async function register(endpoint){
    let url;
    try{url=new URL(String(endpoint));}catch{throw new Error("请先填写同步服务地址。");}
    if(!/\/sync\/?$/.test(url.pathname))throw new Error("同步服务地址应以 /sync 结尾。");
    url.pathname=url.pathname.replace(/\/sync\/?$/,"/register");
    const ctrl=new AbortController();
    const timer=setTimeout(()=>ctrl.abort(),12000);
    try{
      const response=await fetch(url.toString(),{method:"POST",headers:{"content-type":"application/json"},body:"{}",signal:ctrl.signal});
      const data=await response.json().catch(()=>({}));
      if(response.status===429)throw new Error("获取次数较多，请稍后再试。");
      if(!response.ok)throw new Error("暂时无法获取令牌，请稍后重试。");
      if(data.ok!==true||typeof data.token!=="string"||data.token.length<32||data.token.length>256)throw new Error("服务返回不完整，请重新获取。");
      return data.token;
    }catch(error){
      if(error.name==="AbortError")throw new Error("获取超时，请检查网络后重试。");
      if(/Failed to fetch|NetworkError|Load failed/.test(error.message))throw new Error("网络连接失败，请检查网络后重试。");
      throw error;
    }finally{clearTimeout(timer);}
  }
  async function copy(token){
    if(!token)throw new Error("请先获取或填写令牌。");
    try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(token);return;}}catch{}
    const input=document.createElement("textarea");input.value=token;input.readOnly=true;
    input.style.cssText="position:fixed;left:-9999px;top:0";document.body.appendChild(input);input.select();
    const ok=document.execCommand("copy");input.remove();
    if(!ok)throw new Error("未能复制，请展开令牌后手动复制。");
  }
  root.SangeToken={register,copy};
})(globalThis);
