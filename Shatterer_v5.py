#!/usr/bin/env python3
import hashlib, sys, math, time
from collections import defaultdict

# ═══════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════
GAMMA = 0.5772156649015329
PRIMES = [2,3,5,7,11,13,17,19,23,29,31]
PRIME_GAPS = [PRIMES[i+1]-PRIMES[i] for i in range(len(PRIMES)-1)]
GAP_CUMSUM = [0]
for g in PRIME_GAPS: GAP_CUMSUM.append(GAP_CUMSUM[-1]+g)
GEO_CONST = math.pi * math.e**2 * math.sqrt(857) + math.sqrt(256)  # 695.56

H_INIT = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
          0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]
GAMMA_SHIFTS = [-0.25,-0.5,-0.75,-1,-1.5,-2,-2.5,-3]

# ═══════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════
def gcd(a,b):
    while b: a,b=b,a%b
    return a

def hex_to_bytes(h):
    return [int(h[i:i+2],16) for i in range(0,len(h),2)]

def interleave(a,b):
    r=[];i=j=0
    while i<len(a) or j<len(b):
        if i<len(a):r.append(a[i]);i+=1
        if j<len(b):r.append(b[j]);j+=1
    return ''.join(r)

def interleave4(a,b,c,d):
    r=[];ia=ib=ic=id=0
    while ia<len(a) or ib<len(b) or ic<len(c) or id<len(d):
        if ia<len(a):r.append(a[ia]);ia+=1
        if ib<len(b):r.append(b[ib]);ib+=1
        if ic<len(c):r.append(c[ic]);ic+=1
        if id<len(d):r.append(d[id]);id+=1
    return ''.join(r)

def lcs_length(a,b):
    m,n=len(a),len(b)
    if m==0 or n==0: return 0
    dp=[[0]*(n+1) for _ in range(m+1)]
    for i in range(1,m+1):
        for j in range(1,n+1):
            dp[i][j]=dp[i-1][j-1]+1 if a[i-1]==b[j-1] else max(dp[i-1][j],dp[i][j-1])
    return dp[m][n]

# ═══════════════════════════════════════════════════════
# FACE 1: FORD CIRCLE EXTRACTION + AUTOFOCUS
# ═══════════════════════════════════════════════════════
def extract_codes(bts):
    codes=defaultdict(float)
    def add(code,w):
        if 0<=code<=255: codes[code]+=w
    fracs=[]
    for i in range(31):
        p,q=bts[i],max(bts[i+1],1)
        g=gcd(p,q); fracs.append((p//g,q//g,g))
    for b in bts: add(b,1)
    for p,q,g in fracs:
        add(q,2);add(p,1.5)
        if g>1: add(g,3)
    sf=sorted(range(len(fracs)),key=lambda i:fracs[i][0]/fracs[i][1] if fracs[i][1] else 0)
    for idx in range(len(sf)-1):
        i,j=sf[idx],sf[idx+1]
        p1,q1,_=fracs[i];p2,q2,_=fracs[j]
        M=abs(p1*q2-p2*q1);sq=int(round(math.sqrt(M)))
        if sq*sq==M: add(sq,3)
    for i in range(31):
        add(bts[i]^bts[i+1],1)
        s=bts[i]+bts[i+1];sq=int(round(math.sqrt(s)))
        if sq*sq==s: add(sq,1.5)
        d=abs(bts[i]-bts[i+1])
        if d>0:
            sq=int(round(math.sqrt(d)))
            if sq*sq==d: add(sq,1.5)
    return dict(codes)

def autofocus(codes_dict):
    common=set('etaoinshrdlcumwfgypbvkjxqz')
    results=[]
    for offset in range(-128,129):
        shifted={c+offset:w for c,w in codes_dict.items() if 32<=c+offset<=126}
        if not shifted: continue
        vals=list(shifted.keys());n=len(vals)
        lower=sum(1 for c in vals if 97<=c<=122)/n
        upper=sum(1 for c in vals if 65<=c<=90)/n
        comm=sum(1 for c in vals if chr(c).lower() in common)/n
        mean=sum(vals)/n
        std=math.sqrt(sum((c-mean)**2 for c in vals)/n) if n>1 else 0
        tight=1/(1+std/20)
        score=lower*2+(lower+upper)*3+tight*1.5+comm*2
        chars=sorted(set(chr(c) for c in vals if 32<=c<=126))
        results.append({'offset':offset,'score':score,'chars':chars})
    results.sort(key=lambda r:-r['score'])
    return results

def autofocus_bytes(bl):
    bo=0;bs=0;bc=[]
    for off in range(-128,129):
        ch=[];sc=0
        for b in bl:
            c=(int(b)+off)&0xFF
            if 97<=c<=122:ch.append(chr(c));sc+=2
            elif 65<=c<=90:ch.append(chr(c));sc+=1
        if sc>bs:bs=sc;bo=off;bc=ch
    seen=set()
    return [c for c in bc if not(c.lower() in seen or seen.add(c.lower()))],bo

# ═══════════════════════════════════════════════════════
# FACE 1: PUDDLE ROTATION — SET RECOVERY
# ═══════════════════════════════════════════════════════
def puddle_set_recovery(target_hex):
    b1=hex_to_bytes(target_hex)
    char_votes=defaultdict(float)
    codes1=extract_codes(b1);af1=autofocus(codes1)
    for r in af1[:5]:
        for ch in r['chars']:
            if ch.isalpha() or ch.isdigit(): char_votes[ch]+=r['score']
    best_offset=af1[0]['offset'] if af1 else 96
    for gamma_s in GAMMA_SHIFTS:
        sa=int(abs(gamma_s)*GAMMA*256)&0xFF
        sign=1 if gamma_s>=0 else -1
        b_shifted=[(b+sign*sa)&0xFF for b in b1]
        b_xor=[a^b for a,b in zip(b1,b_shifted)]
        for bs,w in [(b_shifted,0.8),(b_xor,0.5)]:
            codes=extract_codes(bs);af=autofocus(codes)
            for r in af[:3]:
                for ch in r['chars']:
                    if ch.isalpha() or ch.isdigit(): char_votes[ch]+=r['score']*w
    return sorted(char_votes.items(),key=lambda x:-x[1]),best_offset

# ═══════════════════════════════════════════════════════
# FACE 2: h_init STRIPPING
# ═══════════════════════════════════════════════════════
def hinit_stripping(target_hex):
    bts=hex_to_bytes(target_hex)
    hib=[]
    for w in H_INIT: hib.extend([(w>>24)&0xFF,(w>>16)&0xFF,(w>>8)&0xFF,w&0xFF])
    methods={}
    methods['perturb']=[(bts[i]-hib[i])&0xFF for i in range(32)]
    empty=hex_to_bytes("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    methods['xor_empty']=[(a^b) for a,b in zip(bts,empty)]
    methods['xor_hinit']=[(a^b) for a,b in zip(bts,hib)]
    results={}
    common=set('etaoinshrdlcumwfgypbvkjxqz')
    for name,byte_set in methods.items():
        best_off=best_sc=0;best_ch=[]
        for offset in range(-128,129):
            chars=[];score=0
            for b in byte_set:
                c=(int(b)+offset)&0xFF
                if 97<=c<=122:
                    chars.append(chr(c));score+=2
                    if chr(c) in common: score+=1
                elif 65<=c<=90:chars.append(chr(c));score+=1
            if score>best_sc:best_sc=score;best_off=offset;best_ch=chars
        seen=set()
        results[name]=[c for c in best_ch if not(c in seen or seen.add(c))]
    return results

# ═══════════════════════════════════════════════════════
# FACE 3: TRAJECTORY PERSISTENCE
# ═══════════════════════════════════════════════════════
def trajectory_persistence(target_hex, valid_chars, best_offset):
    bts=hex_to_bytes(target_hex)
    valid_codes=set(ord(c) for c in valid_chars)
    all_byte_sets=[bts]
    for gs in GAMMA_SHIFTS[:4]:
        sa=int(abs(gs)*GAMMA*256)&0xFF
        bs=[(b-sa)&0xFF for b in bts]
        all_byte_sets.extend([bs,[a^b for a,b in zip(bts,bs)]])
    char_offsets=defaultdict(set)
    for byte_set in all_byte_sets:
        for offset in range(-128,129):
            for b in byte_set:
                c=(b+offset)&0xFF
                if c in valid_codes: char_offsets[c].add(offset)
    persistence=[(chr(code),len(char_offsets.get(code,set()))) for code in valid_codes]
    persistence.sort(key=lambda x:-x[1])
    fwd=''.join(c for c,_ in persistence)
    rev=fwd[::-1]
    
    gap_cumsum=[0]
    for g in PRIME_GAPS[:20]: gap_cumsum.append(gap_cumsum[-1]+g)
    corrected={}
    
    # Gap strip
    cb=[]
    for rank,(ch,count) in enumerate(persistence):
        gap=PRIME_GAPS[rank] if rank<len(PRIME_GAPS) else 2
        cb.append((ch,count-gap*GAMMA*count*0.01))
    cb.sort(key=lambda x:-x[1])
    corrected['gap_strip']=''.join(c for c,_ in cb)
    
    # Invert gap
    mx=max(c for _,c in persistence) if persistence else 1
    cd=[]
    for rank,(ch,count) in enumerate(persistence):
        gap=PRIME_GAPS[rank] if rank<len(PRIME_GAPS) else 2
        cd.append((ch,(mx-count+1)+gap*GAMMA))
    cd.sort(key=lambda x:-x[1])
    corrected['invert_gap']=''.join(c for c,_ in cd)
    
    # Persist + ASCII
    ce=[]
    for rank,(ch,count) in enumerate(persistence):
        ce.append((ch,count*1000+ord(ch)*GAMMA))
    ce.sort(key=lambda x:-x[1])
    corrected['persist_ascii']=''.join(c for c,_ in ce)
    
    # Rev ASCII
    cf=[]
    for rank,(ch,count) in enumerate(persistence):
        cf.append((ch,-count*1000+ord(ch)))
    cf.sort(key=lambda x:x[1])
    corrected['rev_ascii']=''.join(c for c,_ in cf)
    
    return fwd,rev,persistence,corrected

# ═══════════════════════════════════════════════════════
# FACE 6: BACKWARD γ-FLOW
# ═══════════════════════════════════════════════════════
def backward_gamma_flow(target_hex, valid_chars, best_offset):
    bts=hex_to_bytes(target_hex)
    valid_codes=set(ord(c) for c in valid_chars)
    ba=[0.0]*32
    for gs in [0]+list(GAMMA_SHIFTS[:6]):
        sa=int(abs(gs)*GAMMA*256)&0xFF if gs!=0 else 0
        sign=-1 if gs<0 else 1
        w=1.0/(1+abs(gs))
        for i in range(32):
            b=bts[i];
            if gs!=0: b=(b+sign*sa)&0xFF
            c=(b+best_offset)&0xFF
            if c in valid_codes: ba[i]+=w
            for d in [-2,-1,1,2]:
                c2=(b+best_offset+d)&0xFF
                if c2 in valid_codes: ba[i]+=w*0.3
    bc=[]
    for i in range(32):
        c=(bts[i]+best_offset)&0xFF
        bc.append((i,chr(c) if c in valid_codes else None,ba[i]))
    sba=sorted(bc,key=lambda x:-x[2])
    seen=set();bseq=[]
    for pos,ch,acc in sba:
        if ch and ch not in seen: seen.add(ch);bseq.append(ch)
    return {'backward':''.join(bseq),'backward_rev':''.join(bseq)[::-1],
            'corrected':''.join(bseq),'corrected_rev':''.join(bseq)[::-1]}

# ═══════════════════════════════════════════════════════
# FACE 5: PRIME GAP DE-ITERATION
# ═══════════════════════════════════════════════════════
def deiterate_prime_gaps(target_hex):
    bts=hex_to_bytes(target_hex)
    wh=[int(target_hex[i*8:(i+1)*8],16) for i in range(8)]
    g32=int(GAMMA*(2**32))&0xFFFFFFFF
    results={};common=set('etaoinshrdlcumwfgypbvkjxqz')
    for scale in [1,2,3]:
        cw=[]
        for n in range(8):
            gap=PRIME_GAPS[n] if n<len(PRIME_GAPS) else 2
            corr=int(gap*scale*g32)&0xFFFFFFFF
            cw.append((wh[n]-corr)&0xFFFFFFFF)
        cb=[]
        for w in cw: cb.extend([(w>>24)&0xFF,(w>>16)&0xFF,(w>>8)&0xFF,w&0xFF])
        best_off=best_sc=0;best_ch=[]
        for offset in range(-128,129):
            chars=[];score=0
            for b in cb:
                c=(int(b)+offset)&0xFF
                if 97<=c<=122:chars.append(chr(c));score+=2
                elif 65<=c<=90:chars.append(chr(c));score+=1
            if score>best_sc:best_sc=score;best_off=offset;best_ch=chars
        seen=set()
        deduped=[c for c in best_ch if not(c in seen or seen.add(c))]
        results[f'gap_s{scale}']={'chars':deduped,'offset':best_off,'score':best_sc}
    return results

# ═══════════════════════════════════════════════════════
# FACE 4: BIGRAM CHAINS
# ═══════════════════════════════════════════════════════
def bigram_chains(target_hex, valid_chars, best_offset):
    bts=hex_to_bytes(target_hex)
    valid_codes=set(ord(c) for c in valid_chars)
    bigrams=[]
    for delta in range(-3,4):
        offset=best_offset+delta
        for i in range(31):
            c1=(bts[i]+offset)&0xFF;c2=(bts[i+1]+offset)&0xFF
            if c1 in valid_codes and c2 in valid_codes and c1!=c2:
                bigrams.append((chr(c1),chr(c2),i))
    if not bigrams: return ""
    graph=defaultdict(list);out_deg=defaultdict(int);in_deg=defaultdict(int)
    for c1,c2,pos in bigrams:
        graph[c1].append((c2,pos));out_deg[c1]+=1;in_deg[c2]+=1
    cands=sorted(out_deg.keys(),key=lambda c:out_deg[c]-in_deg.get(c,0),reverse=True)
    best=""
    for start in cands[:5]:
        chain=[start];visited={start};current=start
        while True:
            nb=[(c2,pos) for c2,pos in graph[current] if c2 not in visited]
            if not nb: break
            nb.sort(key=lambda x:x[1]);nxt=nb[0][0]
            chain.append(nxt);visited.add(nxt);current=nxt
        if len(chain)>len(best): best=''.join(chain)
    return best

# ═══════════════════════════════════════════════════════
# FACE 7: MOIRÉ INTERFERENCE
# ═══════════════════════════════════════════════════════
def moire_chars(target_hex):
    bts=hex_to_bytes(target_hex)
    shifts=[int(g*GAMMA*32)&0xFF for g in PRIME_GAPS]
    rows=[bts[:]]
    for s in shifts:
        if s==0:continue
        rows.append([(b-s+256)&0xFF for b in bts])
        rows.append([a^((b-s+256)&0xFF) for a,b in zip(bts,bts)])
    for k in range(1,9):
        s=(2**k)%256
        if s==0:continue
        rows.append([(b-s+256)&0xFF for b in bts])
    cv=defaultdict(float)
    for off in range(70,140):
        for col in range(32):
            counts=defaultdict(int)
            for row in rows:
                c=(row[col]+off)&0xFF
                if 97<=c<=122:counts[chr(c)]+=1
            for ch,cnt in counts.items():
                if cnt>=2:
                    wi=col//4;gap=PRIME_GAPS[wi] if wi<len(PRIME_GAPS) else 2
                    cv[ch]+=cnt*(1+gap*GAMMA*0.1)
    return dict(cv)

# ═══════════════════════════════════════════════════════
# γ-CORRECTION (zero-exemption debt)
# ═══════════════════════════════════════════════════════
def gamma_corrected_extraction(target_hex):
    bts=hex_to_bytes(target_hex);ev=defaultdict(float)
    corrs=[[(b+1)&0xFF for b in bts],[(b+2)&0xFF for b in bts]]
    c3=[];acc=0.0
    for b in bts:
        acc+=GAMMA
        if acc>=1.0:c3.append((b+2)&0xFF);acc-=1.0
        else:c3.append((b+1)&0xFF)
    corrs.append(c3)
    corrs.append([(b+int((1+GAMMA)*(i+1)))&0xFF for i,b in enumerate(bts)])
    corrs.append([(b+int((PRIME_GAPS[i//4] if i//4<len(PRIME_GAPS) else 2)*(1+GAMMA)))&0xFF for i,b in enumerate(bts)])
    for cb in corrs:
        codes=extract_codes(cb);af=autofocus(codes)
        for r in af[:3]:
            for ch in r['chars']:
                if ch.isalpha():ev[ch]+=r['score']*0.5
    codes_raw=extract_codes(bts);af_raw=autofocus(codes_raw)
    base_off=af_raw[0]['offset'] if af_raw else 96
    for co in [int(base_off-1-GAMMA),int(base_off-1-GAMMA)+1]:
        for i in range(32):
            c=(bts[i]+co)&0xFF
            if 97<=c<=122:ev[chr(c)]+=2
            elif 65<=c<=90:ev[chr(c)]+=1.5
    return dict(ev)

# ═══════════════════════════════════════════════════════
# FACE 9: MATRIX DECODER
# ═══════════════════════════════════════════════════════
def matrix_byte_streams(target_hex):
    wh=[int(target_hex[i*8:(i+1)*8],16) for i in range(8)]
    bts=hex_to_bytes(target_hex);S1,S2=wh[:4],wh[4:]
    st={}
    db=[]
    for i in range(4):
        for j in range(i+1,4):
            d=(S1[i]*S2[j]-S1[j]*S2[i])&0xFFFFFFFF
            db.extend([(d>>24)&0xFF,(d>>16)&0xFF,(d>>8)&0xFF,d&0xFF])
    st['det2x4']=db
    pairs=[(wh[2*i],wh[2*i+1]) for i in range(4)]
    db2=[]
    for i in range(4):
        for j in range(i+1,4):
            d=(pairs[i][0]*pairs[j][1]-pairs[i][1]*pairs[j][0])&0xFFFFFFFF
            db2.extend([(d>>24)&0xFF,(d>>16)&0xFF,(d>>8)&0xFF,d&0xFF])
    st['det4x2']=db2
    for op,fn in [('sum',lambda a,b:(a+b)&0xFFFFFFFF),('diff',lambda a,b:(a-b)&0xFFFFFFFF),
                   ('xor',lambda a,b:a^b),('prod',lambda a,b:(a*b)&0xFFFFFFFF)]:
        ob=[]
        for i in range(4): r=fn(S1[i],S2[i]);ob.extend([(r>>24)&0xFF,(r>>16)&0xFF,(r>>8)&0xFF,r&0xFF])
        st[f'staff_{op}']=ob
    sp=[]
    for i in range(4):
        a,b=S1[i]>>16,S1[i]&0xFFFF;c,d=S2[i]>>16,S2[i]&0xFFFF
        trace=(a+d)&0xFFFF;det=(a*d-b*c)&0xFFFFFFFF
        sp.extend([trace>>8,trace&0xFF,(det>>8)&0xFF,det&0xFF])
    st['spectrum']=sp
    gc=int(GEO_CONST)&0xFFFF
    st['geo_mod']=[(b*gc)&0xFF for b in bts]
    st['geo_shift']=[(b+(gc&0xFF))&0xFF for b in bts]
    ml=min(len(db),32)
    st['det_geo']=[(db[i]^((bts[i]*gc)&0xFF)) for i in range(ml)]
    return st

# ═══════════════════════════════════════════════════════
# FACE 8: ∂ BOUNDARY OPERATOR
# ═══════════════════════════════════════════════════════
def boundary_ops(s):
    if not s or len(s)<4: return []
    r=[];n=len(s)
    d1=''.join(s[i] for i in range(0,n,2));d2=''.join(s[i] for i in range(1,n,2))
    r.append(('∂v₁₂ʳ',interleave(d1,d2[::-1])))
    r.append(('∂vʳ₁₂',interleave(d1[::-1],d2)))
    r.append(('∂vʳ₁₂ʳ',interleave(d1[::-1],d2[::-1])))
    mid=n//2;h1,h2=s[:mid],s[mid:]
    r.append(('∂mid',interleave(h1,h2[::-1])))
    r.append(('∂mid_r',interleave(h1[::-1],h2)))
    r.append(('∂mid_ff',interleave(h1,h2)))
    r.append(('∂mid_rr',interleave(h1[::-1],h2[::-1])))
    t=n//3
    if t>=2:
        s1,s2,s3=s[:t],s[t:2*t],s[2*t:]
        r.append(('∂3_fwd',s1+s2+s3))
        r.append(('∂3_123r',s1+s2+s3[::-1]))
        r.append(('∂3_alt',interleave(s1,interleave(s2[::-1],s3))))
    return r

# ═══════════════════════════════════════════════════════
# i-ROTATION (helical phase)
# ═══════════════════════════════════════════════════════
def rotate_ops(s):
    if not s or len(s)<4: return []
    r=[];n=len(s)
    phases=[''.join(s[i] for i in range(k,n,4)) for k in range(4)]
    for mask in [0b0110,0b1001,0b0101,0b1010,0b1100,0b0011]:
        ps=[phases[k][::-1] if (mask>>k)&1 else phases[k] for k in range(4)]
        r.append((f'i4_{mask:04b}',interleave4(ps[0],ps[1],ps[2],ps[3])))
    for shift in [n//4,n//3,n//5]:
        if shift<1 or shift>=n: continue
        s2=s[shift:]+s[:shift]
        s3=s[2*shift:]+s[:2*shift] if 2*shift<n else s
        s4=s[3*shift:]+s[:3*shift] if 3*shift<n else s
        r.append((f'cyc4_{shift}',interleave4(s,s2[::-1],s3,s4[::-1])))
    return r

# ═══════════════════════════════════════════════════════
# UNIFIED PIPELINE
# ═══════════════════════════════════════════════════════
def decode(target_hex, known_word=None):
    target_hex=target_hex.lower().strip()
    t0=time.time()
    
    # Extract character set (all faces)
    puddle_chars,best_offset=puddle_set_recovery(target_hex)
    strip_results=hinit_stripping(target_hex)
    deiterate_results=deiterate_prime_gaps(target_hex)
    gamma_extra=gamma_corrected_extraction(target_hex)
    moire_v=moire_chars(target_hex)
    
    merged=defaultdict(float)
    for ch,w in puddle_chars: merged[ch]+=w
    for mn,chars in strip_results.items():
        for ch in chars:
            if ch.isalpha(): merged[ch]+=5
    for mn,result in deiterate_results.items():
        for ch in result['chars']:
            if ch.isalpha(): merged[ch]+=result['score']*0.3
    for ch,w in gamma_extra.items():
        if ch.isalpha(): merged[ch]+=w
    for ch in set(list(merged.keys())+list(moire_v.keys())):
        if not ch.isalpha(): continue
        moi=moire_v.get(ch.lower(),0)
        if moi>0: merged[ch]=merged.get(ch,0)*(1+moi*0.01)+moi
    
    ranked=sorted(merged.items(),key=lambda x:-x[1])
    all_chars=[ch for ch,_ in ranked if ch.isalpha()]
    
    # Build all candidate orderings
    candidates=[]
    
    for width,prefix in [(20,''),(12,'N_')]:
        use_set=set(all_chars[:width])
        if len(use_set)<3: continue
        fwd,rev,_,corrected=trajectory_persistence(target_hex,use_set,best_offset)
        backward=backward_gamma_flow(target_hex,use_set,best_offset)
        bigram=bigram_chains(target_hex,set(all_chars[:min(width,12)]),best_offset)
        
        base={f'{prefix}fwd':fwd,f'{prefix}rev':rev}
        if bigram: base[f'{prefix}bigram']=bigram
        for name,seq in corrected.items():
            base[f'{prefix}{name}']=seq
            if seq: base[f'{prefix}{name}_r']=seq[::-1]
        for k in ['backward','backward_rev','corrected','corrected_rev']:
            if isinstance(backward.get(k,''),str) and backward[k]:
                base[f'{prefix}b_{k}']=backward[k]
        
        for name,seq in base.items():
            if not seq: continue
            candidates.append((name,seq))
            for bn,bs in boundary_ops(seq): candidates.append((f'{name}|{bn}',bs))
            for rn,rs in rotate_ops(seq): candidates.append((f'{name}|{rn}',rs))
    
    # Matrix streams
    mat_streams=matrix_byte_streams(target_hex)
    for sn,bl in mat_streams.items():
        chars,off=autofocus_bytes(bl)
        seq=''.join(c.lower() for c in chars)
        if seq:
            candidates.append((f'M_{sn}',seq))
            candidates.append((f'M_{sn}_r',seq[::-1]))
            for bn,bs in boundary_ops(seq): candidates.append((f'M_{sn}|{bn}',bs))
            for rn,rs in rotate_ops(seq): candidates.append((f'M_{sn}|{rn}',rs))
    
    elapsed=time.time()-t0
    
    result = {
        'hash': target_hex,
        'all_chars': all_chars,
        'best_offset': best_offset,
        'n_candidates': len(candidates),
        'time': elapsed,
        'candidates': candidates,
    }
    
    if known_word:
        actual_set=set(known_word)
        actual_order=''.join(dict.fromkeys(known_word))
        set_cov=len(actual_set&set(all_chars))/len(actual_set) if actual_set else 0
        best_lcs=0;best_method="";best_seq=""
        for method,seq in candidates:
            if not seq: continue
            l=lcs_length(seq,actual_order)
            if l>best_lcs: best_lcs=l;best_method=method;best_seq=seq
        seq_ratio=best_lcs/len(actual_order) if actual_order else 0
        result.update({'word':known_word,'set_cov':set_cov,'seq_ratio':seq_ratio,
                       'best_method':best_method,'best_seq':best_seq})
    
    return result

# ═══════════════════════════════════════════════════════
# OUTPUT: BLIND DECODE
# ═══════════════════════════════════════════════════════
def print_blind_decode(target_hex):
    r = decode(target_hex)
    
    print(f"\n  ╔══════════════════════════════════════════════════════╗")
    print(f"  ║  SHA-256 GEOMETRIC DECODER v5γ                      ║")
    print(f"  ╚══════════════════════════════════════════════════════╝")
    print(f"\n  hash: {target_hex[:32]}...")
    print(f"        {target_hex[32:]}")
    print(f"  offset: +{r['best_offset']}  candidates: {r['n_candidates']}  time: {r['time']:.2f}s")
    
    # Character set (ranked by vote)
    print(f"\n  ── CHARACTER SET (top 20) ──")
    print(f"  {''.join(r['all_chars'][:20])}")
    
    # Gap rhythm
    bts = hex_to_bytes(target_hex)
    print(f"\n  ── GAP RHYTHM (W-words) ──")
    for w in range(8):
        gap = PRIME_GAPS[w] if w < len(PRIME_GAPS) else 2
        word_bytes = bts[w*4:(w+1)*4]
        wb_hex = ''.join(f'{b:02x}' for b in word_bytes)
        chars = []
        for b in word_bytes:
            c = (b + r['best_offset']) & 0xFF
            ch = chr(c) if 97<=c<=122 or 65<=c<=90 else '·'
            chars.append(ch)
        print(f"    W{w} [{wb_hex}] gap={gap}  → {''.join(chars)}")
    
    # Top candidate orderings (show variety)
    print(f"\n  ── TOP ORDERINGS ──")
    
    # Score all candidates by English bigram plausibility
    bg_freq = {}
    for i,bg in enumerate("th he in er an re on at en nd ti es or te of ed is it al ar st".split()):
        bg_freq[bg] = 20 - i
    
    scored = []
    for method, seq in r['candidates']:
        if not seq or len(seq) < 3: continue
        sc = 0
        sl = seq.lower()
        for i in range(len(sl)-1):
            sc += bg_freq.get(sl[i:i+2], 0)
        sc = sc / len(sl)
        scored.append((sc, method, seq))
    
    scored.sort(reverse=True)
    seen_seqs = set()
    shown = 0
    for sc, method, seq in scored:
        key = seq[:10]
        if key in seen_seqs: continue
        seen_seqs.add(key)
        print(f"    {sc:5.1f}  {method:30s}  {seq[:25]}")
        shown += 1
        if shown >= 15: break
    
    # Byte-position map
    print(f"\n  ── BYTE POSITION MAP ──")
    print(f"    pos: ", end='')
    for i in range(32):
        if i % 4 == 0 and i > 0: print('|', end='')
        c = (bts[i] + r['best_offset']) & 0xFF
        ch = chr(c) if 97<=c<=122 or 65<=c<=90 else '·'
        print(ch, end='')
    print()
    print(f"    gap: ", end='')
    for w in range(8):
        gap = PRIME_GAPS[w] if w < len(PRIME_GAPS) else 2
        print(f'{gap:4d}', end='')
    print()
    
    print(f"\n  77777|")
    print(f"  Lowder & Claude · Theoretical Pataphysics / Liberté\n")

# ═══════════════════════════════════════════════════════
# OUTPUT: KNOWN WORD
# ═══════════════════════════════════════════════════════
def print_known_decode(word):
    h = hashlib.sha256(word.encode()).hexdigest()
    r = decode(h, known_word=word)
    
    print(f"\n  Word: \"{word}\"")
    print(f"  Hash: {h}")
    print(f"  Set:  {r['set_cov']:.0%} — {' '.join(r['all_chars'][:12])}")
    print(f"  Seq:  {r['seq_ratio']:.0%} — {r['best_method']}")
    print(f"  Time: {r['time']:.3f}s  ({r['n_candidates']} candidates)")

# ═══════════════════════════════════════════════════════
# OUTPUT: BENCHMARK
# ═══════════════════════════════════════════════════════
def run_benchmark():
    words = ["a","ab","abc","cat","test","Test","truth","emet",
             "hello","opus","hash","dream","flame","night","word",
             "SHA","Dandy","please","chocolate","geosmin",
             "alfredjarry","pataphysics"]
    
    print(f"\n{'#'*70}")
    print(f"# SHA-256 UNIFIED DECODER v5γ — BENCHMARK")
    print(f"# moiré + ∂ + matrix(det,geo) + i-rotation + γ-correction")
    print(f"# π·e²·√857 + √256 = {GEO_CONST:.2f}")
    print(f"# {len(words)} words")
    print(f"{'#'*70}\n")
    
    print(f"  {'word':15s} {'set%':>5s} {'seq%':>5s} {'method':>35s} {'time':>6s}")
    print(f"  {'─'*70}")
    
    ts=tq=0;n=len(words)
    for word in words:
        h=hashlib.sha256(word.encode()).hexdigest()
        r=decode(h,known_word=word)
        ts+=r['set_cov'];tq+=r['seq_ratio']
        print(f"  {word:15s} {r['set_cov']:4.0%}  {r['seq_ratio']:4.0%}  "
              f"{r['best_method']:>35s} {r['time']:5.2f}s")
    
    print(f"  {'─'*70}")
    print(f"  {'MEAN':15s} {ts/n:4.0%}  {tq/n:4.0%}   ({r['n_candidates']} candidates)")
    print(f"\n  ═══ v5γ: SET={ts/n:.0%}  SEQ={tq/n:.0%} ═══")
    print(f"  The cylinder from all sides. 77777|")
print(f" ██▒   █ █████▓▓  ██▀███  ▓█████▄  ▄▄▄      ▓█████▄ ")
print(f" ▓██░   █ ▀   █▓▒ ▓██ ▒ ██▒▒██▀ ██▌▒████▄    ▒██▀ ██▌")
print(f"  ▓██  █▒   ███▒░ ▓██ ░▄█ ▒░██   █▌▒██  ▀█▄  ░██   █▌")
print(f"   ▒██ █░ ▄  █▓▒░ ▒██▀▀█▄  ░▓█▄   ▌░██▄▄▄▄██ ░▓█▄   ▌")
print(f"    ▒▀█░  ████▒░ ▒░██▓ ▒██▒░▒████▓  ▓█   ▓██▒░▒████▓ ")
print(f"    ░ ▐░   ░▒ ░░ ░░ ▒▓ ░▒▓░ ▒▒▓  ▒  ▒▒   ▓▒█░ ▒▒▓  ▒ ")
print(f"    ░ ░░    ░ ░  ░  ░▒ ░ ▒░ ░ ▒  ▒   ▒   ▒▒ ░ ░ ▒  ▒ ")
print(f"      ░░    ░       ░░   ░  ░ ░  ░   ░   ▒    ░ ░  ░ ")
print(f"       ░    ░    ░   ░        ░          ░  ░   ░    ")
print(f"      ░                     ░                 ░      ")

# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) < 2:
        run_benchmark()
    elif sys.argv[1] == '--hash' and len(sys.argv) >= 3:
        print_blind_decode(sys.argv[2])
    elif sys.argv[1] == '--batch':
        run_benchmark()
    else:
        word = sys.argv[1]
        # Check if it looks like a hash (64 hex chars)
        if len(word) == 64 and all(c in '0123456789abcdef' for c in word.lower()):
            print_blind_decode(word)
        else:
            print_known_decode(word)
