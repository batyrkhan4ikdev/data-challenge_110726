const params = new URLSearchParams(location.search);
const data = params.get('data') ?? JSON.stringify({
  apiBase: 'http://127.0.0.1:8806/api',
  route: params.get('route') || '#/dialogs/DEV',
});
const source = new URL('cqa_/index.htm', 'http://127.0.0.1:8807/');
source.searchParams.set('data', data);
source.searchParams.set('id', '{local-record}');
source.searchParams.set('typename', 'incident');
document.getElementById('resource').src = source.href;
