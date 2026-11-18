"""Controle do confundidor 'comprimento': compara só L_norte × L_leste (mesmo comprimento Manhattan, ~igual km)."""
import sys, runpy, numpy as np
sys.argv=["x"]
src = open(__import__('pathlib').Path(__file__).with_name('ordem_rotas.py')).read().split("linhas = []")[0]
exec(src)
conc=disc=cp=dp=n=0; difkm=[]
for ini in REPORTADAS:
    hist=b.pont(range(1,ini)); pers=b.pont(range(ini-LARGURA,ini)); alvo=b.pont(range(ini,ini+LARGURA))
    for f in range(5):
        for rt in pares:
            if "L_norte" not in rt or "L_leste" not in rt: continue
            a,c=rt["L_norte"],rt["L_leste"]
            ph=score_rota(a,f,hist)[0]-score_rota(c,f,hist)[0]; pp=score_rota(a,f,pers)[0]-score_rota(c,f,pers)[0]
            ra=score_rota(a,f,alvo)[0]-score_rota(c,f,alvo)[0]
            difkm.append(abs(score_rota(a,f,hist)[1]-score_rota(c,f,hist)[1]))
            if ph==0 or ra==0: continue
            n+=1; conc+= ph*ra>0
            if pp!=0: cp+= pp*ra>0; dp+=1
print("pares L×L:", n, "concordância hist:", round(conc/n,3), "persistência:", round(cp/dp,3), "dif km média:", round(float(np.mean(difkm)),4))
