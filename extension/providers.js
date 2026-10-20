/* AI services reached through their OpenAI-compatible endpoint: the address and a
   suggested model, so choosing a service by name is enough. Shared by Options and
   the welcome page; the local service only sees api_base, api_model and the key. */
globalThis.AnacoObProviders=(()=>{
  const SERVICES=[
    {id:'claude',name:'Claude',base:'https://api.anthropic.com/v1',model:'claude-sonnet-5-5',keys:'https://platform.claude.com/settings/keys'},
    {id:'gemini',name:'Gemini',base:'https://generativelanguage.googleapis.com/v1beta/openai',model:'gemini-3.8-flash',keys:'https://aistudio.google.com/apikey'},
    {id:'openai',name:'OpenAI',base:'https://api.openai.com/v1',model:'gpt-6-luna',keys:'https://platform.openai.com/api-keys'},
    {id:'minimax',name:'MiniMax',base:'https://api.minimax.io/v1',model:'MiniMax-M3.1-Flash',keys:'https://platform.minimax.io/user-center/basic-information/interface-key'},
    {id:'qwen',name:'Qwen',base:'https://dashscope-intl.aliyuncs.com/compatible-mode/v1',model:'qwen-plus',keys:'https://www.alibabacloud.com/help/en/model-studio/get-api-key'},
    {id:'openrouter',name:'OpenRouter',base:'https://openrouter.ai/api/v1',model:'openrouter/auto',keys:'https://openrouter.ai/keys'},
    {id:'ollama',name:'Ollama',base:'http://localhost:11434/v1',model:'llama3.1:8b',local:true},
    {id:'lmstudio',name:'LM Studio',base:'http://localhost:1234/v1',model:'',local:true},
  ];
  const clean=value=>String(value||'').trim().replace(/\/+$/,'');
  // The service a saved address belongs to; anything else is a custom server.
  function match(base){return SERVICES.find(s=>clean(s.base)===clean(base))?.id||'custom';}
  function find(id){return SERVICES.find(s=>s.id===id)||null;}
  return {SERVICES,match,find};
})();
