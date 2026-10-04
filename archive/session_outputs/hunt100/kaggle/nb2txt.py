import re,html,sys
src,dst=sys.argv[1],sys.argv[2]
s=open(src,encoding='utf-8',errors='ignore').read()
s=re.sub(r'<script.*?</script>','',s,flags=re.S); s=re.sub(r'<style.*?</style>','',s,flags=re.S)
s=re.sub(r'<img[^>]*>','[img]',s)
t=re.sub(r'<[^>]+>',' ',s); t=html.unescape(t); t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
open(dst,'w',encoding='utf-8').write(t); print(len(t))
