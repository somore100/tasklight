"""TaskLight V5 — main.py"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading, os, sys
import settings, state, recorder, player, humanizer, presets, network, fps, duplicator, sysmon
from network import net_state as _ns
from sysmon import sys_state as _ss
from fps import fps_state as _fs2
from duplicator import dup_state as _ds
from pynput import keyboard as kb

# ── boot ──────────────────────────────────────────────────────────────────────
settings.load()

# ── theme ─────────────────────────────────────────────────────────────────────
THEMES = {
    "dark":  {"bg":"#161616","bg2":"#202020","bg3":"#1a1a1a","bg4":"#2a2a2a",
              "fg":"#d0d0d0","fg2":"#777777","fg3":"#3a3a3a",
              "red":"#c05050","blue":"#4a8fc4","green":"#50a870",
              "orange":"#c48840","accent":"#4a8fc4","sep":"#252525"},
    "light": {"bg":"#f0f0f0","bg2":"#e2e2e2","bg3":"#d8d8d8","bg4":"#c8c8c8",
              "fg":"#111111","fg2":"#555555","fg3":"#aaaaaa",
              "red":"#b02020","blue":"#1a5a9a","green":"#1a7a40",
              "orange":"#9a5800","accent":"#1a5a9a","sep":"#cccccc"},
}
_tw = []
_ttk_style = None  # set after root created

def T(k): return THEMES[settings.get("theme")][k]
def _reg(w,p,k): _tw.append((w,p,k)); return w

def _apply_ttk_style():
    """Style ttk widgets to match current theme."""
    global _ttk_style
    if _ttk_style is None: return
    bg=T("bg2"); fg=T("fg"); bg3=T("bg3")
    _ttk_style.configure("Vertical.TScrollbar",
                         background=bg3, troughcolor=T("bg"),
                         bordercolor=T("bg"), arrowcolor=fg,
                         darkcolor=bg3, lightcolor=bg3)
    _ttk_style.map("Vertical.TScrollbar",
                   background=[("active",T("bg4")),("!active",bg3)])

def apply_theme():
    for w,p,k in _tw:
        try: w.config(**{p:T(k)})
        except: pass
    _apply_ttk_style()

def toggle_theme():
    settings.set("theme","light" if settings.get("theme")=="dark" else "dark")
    apply_theme()
    theme_btn.config(text="☀" if settings.get("theme")=="dark" else "☾")

# ── hotkeys ───────────────────────────────────────────────────────────────────
_mods = set()
_MOD  = {"ctrl","shift","alt","cmd","super"}
def _kn(key):
    try:
        if hasattr(key,"char") and key.char: return key.char.lower()
        return key.name.lower()
    except: return ""
def _is_mod(k): return any(m in _kn(k) for m in _MOD)
def _cur_mods(): return frozenset(m for m in _MOD if any(m in p for p in _mods))
def _parse(hk):
    parts=[p.strip().lower() for p in hk.split("+")]
    mods=frozenset(p for p in parts if p in _MOD)
    keys=[p for p in parts if p not in _MOD]
    return mods, keys[-1] if keys else ""
def _matches(hk,key):
    mods,main=_parse(hk)
    return _cur_mods()==mods and _kn(key)==main

# ── QUIT (always first) ───────────────────────────────────────────────────────
def emergency_quit():
    state.quit_flag=state.stop_flag=True
    state.is_recording=state.is_playing=False
    humanizer.stop_jitter_solo(); humanizer.stop_clicker_solo()
    duplicator.stop_solo(); fps.stop_monitor(); sysmon.stop()
    network.stop_all(_iface_var.get() if '_iface_var' in dir() else "")
    settings.save()
    try: root.destroy()
    except: pass
    sys.exit(0)

# ── core ──────────────────────────────────────────────────────────────────────
_ml=_kl=None
def toggle_record():
    global _ml,_kl
    if not state.is_recording:
        _ml,_kl=recorder.start_recording(); set_status("recording")
    else:
        recorder.stop_recording(_ml,_kl)
        state.current_preset_name=""
        set_status("idle",f"({len(state.events)} events)")
        _refresh_mini()

def start_playback():
    if not state.events: set_status("idle","nothing recorded"); return
    _push_settings(); set_status("playing")
    def _run():
        try:
            speed=_sf(speed_var.get(),1.0)
            loops=0 if infinite_var.get() else _si(loop_var.get(),1)
            player.play(speed=speed,loop=loops)
        finally:
            if not state.stop_flag: set_status("idle")
    threading.Thread(target=_run,daemon=True).start()

def stop_all():
    state.stop_flag=state.is_recording=state.is_playing=False
    set_status("stopped")

def _sf(v,d=1.0):
    try: return float(v)
    except: return d
def _si(v,d=1):
    try: return int(v)
    except: return d

def _push_settings():
    s=settings.set
    for k,v in [
        ("speed",speed_var.get()),("loops",loop_var.get()),
        ("infinite",infinite_var.get()),("human_enabled",human_var.get()),
        ("delay_addon",delay_addon_var.get()),("delay_min",delay_min_var.get()),
        ("delay_max",delay_max_var.get()),("smooth_addon",smooth_addon_var.get()),
        ("smooth_steps",smooth_steps_var.get()),("jitter_addon",jitter_addon_var.get()),
        ("jitter_px",jitter_px_var.get()),("jitter_max",jitter_max_var.get()),
        ("jitter_aggression",jitter_agg_var.get()),
        ("clicker_addon",clicker_addon_var.get()),
        ("clicker_cps_base",cps_base_var.get()),("clicker_cps_loss",cps_loss_var.get()),
        ("clicker_cps_min",cps_min_var.get()),("clicker_cps_max",cps_max_var.get()),
        ("clicker_hold_min",hold_min_var.get()),("clicker_hold_max",hold_max_var.get()),
        ("clicker_burst_chance",burst_chance_var.get()),
        ("clicker_burst_min",burst_min_var.get()),("clicker_burst_max",burst_max_var.get()),
        ("clicker_slip_chance",slip_var.get()),("failsafe",failsafe_var.get()),
        ("net_ping_host",host_var.get()),("net_show_mini_ping",show_mini_ping_var.get()),
        ("dup_enabled",dup_enabled_var.get()),("dup_addon",dup_addon_var.get()),
        ("dup_count",dup_count_var.get()),("dup_gap_ms",dup_gap_var.get()),
        ("dup_mode",dup_mode_var.get()),("dup_use_jitter",dup_jitter_var.get()),
        ("dup_button",dup_btn_var.get()),("clicker_button",clicker_btn_var.get()),
        ("fps_show_mini",fps_show_mini_var.get()),("fps_prefer_gpu",fps_prefer_gpu_var.get()),
        ("sysmon_enabled",sysmon_enabled_var.get()),("sysmon_interval",sysmon_interval_var.get()),
        ("sysmon_show_cpu",sysmon_cpu_var.get()),("sysmon_show_ram",sysmon_ram_var.get()),
        ("sysmon_show_gpu",sysmon_gpu_var.get()),("sysmon_show_disk",sysmon_disk_var.get()),
        ("sysmon_show_net",sysmon_net_var.get()),("sysmon_show_temp",sysmon_temp_var.get()),
        ("sysmon_show_mini",sysmon_mini_var.get()),("sysmon_show_cores",sysmon_cores_var.get()),
    ]: s(k,v)
    for k,var in _kb_vars.items():
        val=var.get().strip().lower()
        if val: s(k,val)

# ── hotkey listener ───────────────────────────────────────────────────────────
def _on_press(key):
    if _is_mod(key): _mods.add(_kn(key)); return
    acts={
        "hk_quit":emergency_quit,"hk_record":toggle_record,
        "hk_play":start_playback,"hk_stop":stop_all,
        "hk_jitter_solo":lambda:(_jitter_hk()),
        "hk_clicker_solo":lambda:(_clicker_hk()),
        "hk_net_blocker":lambda:(_blocker_hk()),
        "hk_dup_solo":lambda:(_dup_hk()),
    }
    for hk,fn in acts.items():
        if _matches(settings.get(hk),key):
            root.after(0,fn); return
def _on_release(key): _mods.discard(_kn(key))
def _jitter_hk():  humanizer.toggle_jitter_solo();  _refresh_mini()
def _clicker_hk(): humanizer.toggle_clicker_solo(); _refresh_mini()
def _dup_hk():     duplicator.toggle_solo();         _refresh_mini()
def _blocker_hk():
    iface=_iface_var.get()
    if iface: network.toggle_blocker(iface); _refresh_mini(); _refresh_blocker_ui()

_hkl=kb.Listener(on_press=_on_press,on_release=_on_release)
_hkl.daemon=True; _hkl.start()

# ── root ──────────────────────────────────────────────────────────────────────
root=tk.Tk()
root.title("TaskLight")
root.minsize(320,200)
root.configure(bg=T("bg"))
root.attributes("-topmost",settings.get("always_on_top"))
root.protocol("WM_DELETE_WINDOW",emergency_quit)
_reg(root,"bg","bg")

# init ttk style
import tkinter.ttk as _ttk_mod
_ttk_style = _ttk_mod.Style(root)
_ttk_style.theme_use("clam")
_apply_ttk_style()

# placeholder for _iface_var (used in emergency_quit)
_iface_var=tk.StringVar(value=settings.get("net_iface") or "")

# ── status ────────────────────────────────────────────────────────────────────
_SI={"idle":"●","recording":"⏺","playing":"▶","stopped":"■",
     "jitter solo":"◈","clicker solo":"◈","saved":"✓","error":"✗"}
_SC={"idle":"fg2","recording":"red","playing":"blue","stopped":"orange",
     "jitter solo":"green","clicker solo":"green","saved":"green","error":"red"}
def set_status(k,extra=""):
    icon=_SI.get(k,"●"); color=T(_SC.get(k,"fg2"))
    status_var.set(f"{icon}  {k.title()}{'  '+extra if extra else ''}")
    status_lbl.config(fg=color)

# ── widget factories ──────────────────────────────────────────────────────────
def Wf(p,bk="bg",**kw):
    f=tk.Frame(p,bg=T(bk),**kw); _reg(f,"bg",bk); return f
def Wl(p,text,sz=9,ck="fg2",anchor="w",**kw):
    w=tk.Label(p,text=text,font=("Helvetica",sz),bg=T("bg"),fg=T(ck),anchor=anchor,**kw)
    _reg(w,"bg","bg"); _reg(w,"fg",ck); return w
def We(p,var,w=7,bk="bg2"):
    # use bg3 for entries so they're darker than panels, not stark white
    entry_bg = "bg3" if bk=="bg2" else bk
    e=tk.Entry(p,textvariable=var,width=w,bg=T(entry_bg),fg=T("fg"),
               insertbackground=T("accent"),relief="flat",font=("Helvetica",10),
               highlightthickness=1,highlightbackground=T("fg3"),
               highlightcolor=T("accent"),disabledbackground=T("bg2"),
               disabledforeground=T("fg3"))
    _reg(e,"bg",entry_bg);_reg(e,"fg","fg")
    _reg(e,"insertbackground","accent")
    _reg(e,"highlightbackground","fg3")
    _reg(e,"highlightcolor","accent")
    return e
def Wc(p,text,var,cmd=None,sz=9,bk="bg"):
    kw=dict(bg=T(bk),fg=T("fg"),selectcolor=T("bg2"),activebackground=T(bk),
            activeforeground=T("fg"),font=("Helvetica",sz),anchor="w",relief="flat",bd=0)
    if cmd: kw["command"]=cmd
    w=tk.Checkbutton(p,text=text,variable=var,**kw)
    _reg(w,"bg",bk);_reg(w,"fg","fg");_reg(w,"selectcolor","bg2");_reg(w,"activebackground",bk)
    return w

def Wrb(parent, text, var, val, cmd=None, bk="bg2", sz=8):
    """Themed radiobutton."""
    w=tk.Radiobutton(parent,text=text,variable=var,value=val,
                     bg=T(bk),fg=T("fg"),selectcolor=T("bg3"),
                     activebackground=T(bk),activeforeground=T("fg"),
                     font=("Helvetica",sz),relief="flat",bd=0)
    if cmd: w.config(command=cmd)
    _reg(w,"bg",bk);_reg(w,"fg","fg")
    _reg(w,"selectcolor","bg3");_reg(w,"activebackground",bk)
    return w
def Wb(p,text,cmd,bg="bg2",fg="fg",hover="bg3",sz=10,**kw):
    b=tk.Button(p,text=text,command=cmd,bg=T(bg),fg=T(fg),
                activebackground=T(hover),activeforeground=T(fg),
                relief="flat",font=("Helvetica",sz,"bold"),cursor="hand2",bd=0,**kw)
    _reg(b,"bg",bg);_reg(b,"fg",fg);_reg(b,"activebackground",hover)
    b.bind("<Enter>",lambda _:b.config(bg=T(hover)))
    b.bind("<Leave>",lambda _:b.config(bg=T(bg)))
    return b
def Wsep(p):
    f=tk.Frame(p,bg=T("sep"),height=1); _reg(f,"bg","sep")
    f.pack(fill="x",pady=2); return f

# ── collapsible section ───────────────────────────────────────────────────────
class Section:
    def __init__(self,parent,title,key,padx=10):
        self._key=key; self._open=bool(settings.get(key)); self._px=padx
        self.hdr=Wf(parent); self.hdr.pack(fill="x",padx=padx,pady=(4,0))
        self._arr=tk.Label(self.hdr,text="▼" if self._open else "▶",
                           font=("Helvetica",8),cursor="hand2",bg=T("bg"),fg=T("fg3"))
        _reg(self._arr,"bg","bg");_reg(self._arr,"fg","fg3")
        self._arr.pack(side="left",padx=(0,4))
        lbl=tk.Label(self.hdr,text=title.upper(),font=("Helvetica",8,"bold"),
                     cursor="hand2",bg=T("bg"),fg=T("fg3"))
        _reg(lbl,"bg","bg");_reg(lbl,"fg","fg3"); lbl.pack(side="left")
        self.body=Wf(parent)
        if self._open: self.body.pack(fill="x",padx=padx,pady=(1,3))
        for w in (self.hdr,self._arr,lbl): w.bind("<Button-1>",self._toggle)
    def _toggle(self,_=None):
        self._open=not self._open; settings.set(self._key,self._open)
        if self._open:
            self.body.pack(fill="x",padx=self._px,pady=(1,3)); self._arr.config(text="▼")
        else:
            self.body.pack_forget(); self._arr.config(text="▶")

# ══════════════════════════════════════════════════════════════════════════════
#  TITLE BAR
# ══════════════════════════════════════════════════════════════════════════════
title_row=Wf(root); title_row.pack(fill="x",pady=(8,2),padx=8)
tl=tk.Label(title_row,text="TaskLight",font=("Helvetica",13,"bold"),
            bg=T("bg"),fg=T("fg"))
_reg(tl,"bg","bg"); _reg(tl,"fg","fg"); tl.pack(side="left",padx=4)

def toggle_mini():
    mini=not settings.get("mini_mode"); settings.set("mini_mode",mini)
    if mini: full_outer.pack_forget(); root.geometry("320x90"); mini_btn.config(text="⊞")
    else:    full_outer.pack(fill="both",expand=True); root.geometry(""); mini_btn.config(text="⊟")
    _refresh_mini()

def toggle_aot():
    v=not settings.get("always_on_top"); settings.set("always_on_top",v)
    root.attributes("-topmost",v)
    aot_btn.config(fg=T("accent") if v else T("fg3"))

def toggle_layout():
    new="vertical" if settings.get("layout")=="horizontal" else "horizontal"
    settings.set("layout",new); layout_btn.config(text="⊞" if new=="horizontal" else "☰")
    _rebuild_human_layout()

for text,cmd,attr_name in [
    ("⊟",toggle_mini,"mini_btn"),
    ("☀" if settings.get("theme")=="dark" else "☾",toggle_theme,"theme_btn"),
    ("⊞" if settings.get("layout")=="horizontal" else "☰",toggle_layout,"layout_btn"),
    ("📌",toggle_aot,"aot_btn"),
]:
    b=tk.Button(title_row,text=text,command=cmd,bg=T("bg"),fg=T("fg2"),
                relief="flat",font=("Helvetica",11),cursor="hand2",
                activebackground=T("bg"),bd=0)
    _reg(b,"bg","bg");_reg(b,"fg","fg2");_reg(b,"activebackground","bg")
    b.pack(side="right",padx=2)
    globals()[attr_name]=b

aot_btn.config(fg=T("accent") if settings.get("always_on_top") else T("fg3"))

status_var=tk.StringVar(value="●  Idle")
status_lbl=tk.Label(root,textvariable=status_var,font=("Helvetica",9),
                    bg=T("bg"),fg=T("fg2"),anchor="w")
_reg(status_lbl,"bg","bg");_reg(status_lbl,"fg","fg2")
status_lbl.pack(fill="x",padx=12,pady=(0,2))

# ── mini indicators row ───────────────────────────────────────────────────────
mini_row=Wf(root); mini_row.pack(fill="x",padx=12,pady=(0,1))

# second line — system stats
sys_mini_lbl=tk.Label(root,text="",font=("Courier",8),bg=T("bg"),fg=T("fg2"),anchor="w")
_reg(sys_mini_lbl,"bg","bg"); _reg(sys_mini_lbl,"fg","fg2")
sys_mini_lbl.pack(fill="x",padx=12,pady=(0,3))
_mini_labels={}
for key,text,col in [
    ("jitter","◈ Jitter","green"),("clicker","◈ Clicker","green"),
    ("dup","◈ Dup","green"),
    ("blocker","⛔ Blocked","red"),("ping","◎ --","blue"),("fps",None,"green")]:
    lbl=tk.Label(mini_row,text="",font=("Helvetica",8),bg=T("bg"),fg=T(col))
    _reg(lbl,"bg","bg");_reg(lbl,"fg",col)
    _mini_labels[key]=lbl

def _refresh_mini():
    # build list of (label_widget, text) for active items only
    items=[]
    if state.jitter_solo_active:   items.append((_mini_labels["jitter"],"◈ Jitter"))
    if state.clicker_solo_active:  items.append((_mini_labels["clicker"],"◈ Clicker"))
    if _ds.solo_active:            items.append((_mini_labels["dup"],"◈ Dup"))
    if _ns.blocker_active:         items.append((_mini_labels["blocker"],"⛔ Blocked"))
    if _ns.monitor_active and show_mini_ping_var.get():
        rtt=_ns.ping_current
        items.append((_mini_labels["ping"],f"◎ {rtt:.0f}ms" if rtt is not None else "◎ --"))
    if _fs2.active and settings.get("fps_show_mini"):
        cur=_fs2.current
        items.append((_mini_labels["fps"],f"{cur:.0f}fps" if cur is not None else "--fps"))

    # hide all first
    for lbl in _mini_labels.values():
        lbl.pack_forget()
        lbl.config(text="")

    # pack only active ones, left to right, no gaps
    for lbl,text in items:
        lbl.config(text=text)
        lbl.pack(side="left",padx=(0,8))

    # system stats line
    if _ss.active and settings.get("sysmon_show_mini"):
        sys_mini_lbl.config(text=sysmon.mini_str(
            show_cpu  = settings.get("sysmon_show_cpu"),
            show_ram  = settings.get("sysmon_show_ram"),
            show_gpu  = settings.get("sysmon_show_gpu"),
            show_disk = settings.get("sysmon_show_disk"),
            show_net  = settings.get("sysmon_show_net"),
            show_temp = settings.get("sysmon_show_temp"),
        ))
    else:
        sys_mini_lbl.config(text="")

Wsep(root)

# ── main buttons ──────────────────────────────────────────────────────────────
btn_row=Wf(root); btn_row.pack(fill="x",padx=10,pady=4)
rb=Wb(btn_row,"⏺  Record",toggle_record,pady=6,padx=4)
pb=Wb(btn_row,"▶  Play",  start_playback,pady=6,padx=4)
sb=Wb(btn_row,"■  Stop",  stop_all,pady=6,padx=4)
rb.config(fg=T("red"),activeforeground=T("red")); _reg(rb,"fg","red")
pb.config(fg=T("blue"),activeforeground=T("blue")); _reg(pb,"fg","blue")
for i,b in enumerate([rb,pb,sb]):
    b.grid(row=0,column=i,sticky="ew",padx=2); btn_row.columnconfigure(i,weight=1)
Wsep(root)

# ── scrollable container ──────────────────────────────────────────────────────
full_outer=Wf(root); full_outer.pack(fill="both",expand=True)
_canvas=tk.Canvas(full_outer,bg=T("bg"),highlightthickness=0,bd=0)
_reg(_canvas,"bg","bg")
_sb=ttk.Scrollbar(full_outer,orient="vertical",command=_canvas.yview)
_canvas.configure(yscrollcommand=_sb.set)
_sb.pack(side="right",fill="y"); _canvas.pack(side="left",fill="both",expand=True)
_inner=Wf(_canvas); _cwin=_canvas.create_window((0,0),window=_inner,anchor="nw")
def _on_fc(e): _canvas.configure(scrollregion=_canvas.bbox("all"))
def _on_cc(e): _canvas.itemconfig(_cwin,width=e.width)
_inner.bind("<Configure>",_on_fc); _canvas.bind("<Configure>",_on_cc)
def _scroll(e):
    if e.num==4 or e.delta>0:   _canvas.yview_scroll(-1,"units")
    elif e.num==5 or e.delta<0: _canvas.yview_scroll(1,"units")
root.bind("<MouseWheel>",_scroll); root.bind("<Button-4>",_scroll); root.bind("<Button-5>",_scroll)
_dy=[0]
def _mp(e): _dy[0]=e.y_root
def _md(e): dy=_dy[0]-e.y_root; _dy[0]=e.y_root; _canvas.yview_scroll(int(dy/5),"units")
root.bind("<Button-2>",_mp); root.bind("<B2-Motion>",_md)

# ══════════════════════════════════════════════════════════════════════════════
#  PLAYBACK
# ══════════════════════════════════════════════════════════════════════════════
sec_pb=Section(_inner,"Playback","sec_playback")
b=sec_pb.body
r0=Wf(b); r0.pack(fill="x",pady=2)
Wl(r0,"Speed").pack(side="left")
speed_var=tk.StringVar(value=settings.get("speed"))
We(r0,speed_var,5).pack(side="left",padx=(4,14))
Wl(r0,"Loops").pack(side="left")
loop_var=tk.StringVar(value=settings.get("loops"))
We(r0,loop_var,5).pack(side="left",padx=(4,0))
r1=Wf(b); r1.pack(fill="x",pady=2)
infinite_var=tk.BooleanVar(value=settings.get("infinite"))
Wc(r1,"Infinite loop",infinite_var).pack(side="left")
failsafe_var=tk.BooleanVar(value=settings.get("failsafe"))
Wc(r1,"Failsafe (corner stop)",failsafe_var).pack(side="left",padx=(14,0))
Wsep(_inner)

# ══════════════════════════════════════════════════════════════════════════════
#  HUMAN MODE
# ══════════════════════════════════════════════════════════════════════════════
sec_hm=Section(_inner,"Human Mode","sec_human")
hb=sec_hm.body
human_var=tk.BooleanVar(value=settings.get("human_enabled"))
ht=Wf(hb); ht.pack(fill="x",pady=(0,6))
Wc(ht,"Enable human mode",human_var,sz=10).pack(side="left")

def _mf(p):
    f=tk.Frame(p,bg=T("bg2"),highlightthickness=1,highlightbackground=T("bg3"))
    _reg(f,"bg","bg2");_reg(f,"highlightbackground","bg3"); return f
def _mt(p,text,ck="accent"):
    l=tk.Label(p,text=text,font=("Helvetica",9,"bold"),bg=T("bg2"),fg=T(ck),anchor="w")
    _reg(l,"bg","bg2");_reg(l,"fg",ck); l.pack(fill="x",padx=6,pady=(4,2))
def _mr(p,pairs):
    f=tk.Frame(p,bg=T("bg2")); _reg(f,"bg","bg2"); f.pack(fill="x",padx=6,pady=1)
    for lbl,var,w in pairs:
        l=tk.Label(f,text=lbl,font=("Helvetica",8),bg=T("bg2"),fg=T("fg2"))
        _reg(l,"bg","bg2");_reg(l,"fg","fg2"); l.pack(side="left")
        e=We(f,var,w,bk="bg3"); e.pack(side="left",padx=(2,10))
def _mc(p,text,var,cmd=None):
    f=tk.Frame(p,bg=T("bg2")); _reg(f,"bg","bg2"); f.pack(fill="x",padx=6,pady=1)
    return Wc(f,text,var,cmd=cmd,bk="bg2")

delay_addon_var  =tk.BooleanVar(value=settings.get("delay_addon"))
delay_min_var    =tk.StringVar(value=settings.get("delay_min"))
delay_max_var    =tk.StringVar(value=settings.get("delay_max"))
smooth_addon_var =tk.BooleanVar(value=settings.get("smooth_addon"))
smooth_steps_var =tk.StringVar(value=settings.get("smooth_steps"))
jitter_addon_var =tk.BooleanVar(value=settings.get("jitter_addon"))
jitter_px_var    =tk.StringVar(value=settings.get("jitter_px"))
jitter_max_var   =tk.StringVar(value=settings.get("jitter_max"))
jitter_agg_var   =tk.StringVar(value=settings.get("jitter_aggression"))
clicker_addon_var=tk.BooleanVar(value=settings.get("clicker_addon"))
clicker_btn_var  =tk.StringVar(value=settings.get("clicker_button") or "left")
cps_base_var     =tk.StringVar(value=settings.get("clicker_cps_base"))
cps_loss_var     =tk.StringVar(value=settings.get("clicker_cps_loss"))
cps_min_var      =tk.StringVar(value=settings.get("clicker_cps_min"))
cps_max_var      =tk.StringVar(value=settings.get("clicker_cps_max"))
hold_min_var     =tk.StringVar(value=settings.get("clicker_hold_min"))
hold_max_var     =tk.StringVar(value=settings.get("clicker_hold_max"))
burst_chance_var =tk.StringVar(value=settings.get("clicker_burst_chance"))
burst_min_var    =tk.StringVar(value=settings.get("clicker_burst_min"))
burst_max_var    =tk.StringVar(value=settings.get("clicker_burst_max"))
slip_var         =tk.StringVar(value=settings.get("clicker_slip_chance"))

def _build_delay(p):
    f=_mf(p); f.pack(fill="both",expand=True,padx=2,pady=2)
    _mt(f,"① Random Delay","blue")
    _mc(f,"Addon (playback)",delay_addon_var).pack(side="left")
    _mr(f,[("min s",delay_min_var,5),("max s",delay_max_var,5)])
    def _reset():
        D=settings.DEFAULTS
        delay_min_var.set(str(D["delay_min"])); delay_max_var.set(str(D["delay_max"]))
    tk.Button(f,text="Reset defaults",command=_reset,bg=T("bg2"),fg=T("fg3"),
              activebackground=T("bg3"),relief="flat",font=("Helvetica",7),
              cursor="hand2",bd=0).pack(anchor="e",padx=6,pady=(0,6))

def _build_smooth(p):
    f=_mf(p); f.pack(fill="both",expand=True,padx=2,pady=2)
    _mt(f,"② Smooth Move","blue")
    _mc(f,"Addon (playback)",smooth_addon_var).pack(side="left")
    _mr(f,[("steps",smooth_steps_var,4)])
    def _reset(): smooth_steps_var.set(str(settings.DEFAULTS["smooth_steps"]))
    tk.Button(f,text="Reset defaults",command=_reset,bg=T("bg2"),fg=T("fg3"),
              activebackground=T("bg3"),relief="flat",font=("Helvetica",7),
              cursor="hand2",bd=0).pack(anchor="e",padx=6,pady=(0,6))

def _build_jitter(p):
    f=_mf(p); f.pack(fill="both",expand=True,padx=2,pady=2)
    _mt(f,"③ Jitter","accent")
    _mc(f,"Addon (playback)",jitter_addon_var).pack(side="left")
    hk=settings.get("hk_jitter_solo").upper()
    jbv=tk.BooleanVar(value=state.jitter_solo_active)
    def _jt(): humanizer.toggle_jitter_solo(); _refresh_mini()
    _mc(f,f"Solo [{hk}] (clicks only)",jbv,cmd=_jt).pack(side="left")
    _mr(f,[("px",jitter_px_var,4),("max",jitter_max_var,4)])
    _mr(f,[("aggression 1-10",jitter_agg_var,3)])
    tk.Label(f,text="Solo mode offsets click position only (not cursor movement)",
             bg=T("bg2"),fg=T("fg3"),font=("Helvetica",7),anchor="w",wraplength=200
             ).pack(fill="x",padx=6)
    def _reset():
        D=settings.DEFAULTS
        jitter_px_var.set(str(D["jitter_px"])); jitter_max_var.set(str(D["jitter_max"]))
        jitter_agg_var.set(str(D["jitter_aggression"]))
    tk.Button(f,text="Reset defaults",command=_reset,bg=T("bg2"),fg=T("fg3"),
              activebackground=T("bg3"),relief="flat",font=("Helvetica",7),
              cursor="hand2",bd=0).pack(anchor="e",padx=6,pady=(0,6))

def _build_clicker(p):
    f=_mf(p); f.pack(fill="both",expand=True,padx=2,pady=2)
    _mt(f,"④ Click Humanizer","accent")
    _mc(f,"Addon (playback)",clicker_addon_var).pack(side="left")
    hk=settings.get("hk_clicker_solo").upper()
    cbv=tk.BooleanVar(value=state.clicker_solo_active)
    def _ct(): humanizer.toggle_clicker_solo(); _refresh_mini()
    _mc(f,f"Solo [{hk}]",cbv,cmd=_ct).pack(side="left")

    # button selector
    br=tk.Frame(f,bg=T("bg2")); _reg(br,"bg","bg2"); br.pack(fill="x",padx=6,pady=(2,0))
    tk.Label(br,text="Button:",bg=T("bg2"),fg=T("fg2"),font=("Helvetica",8)).pack(side="left")
    for label,val in [("Left","left"),("Right","right"),("Both","both")]:
        Wrb(br,label,clicker_btn_var,val,
            cmd=lambda: settings.set("clicker_button",clicker_btn_var.get())
            ).pack(side="left",padx=(4,0))
    _mr(f,[("CPS base",cps_base_var,4),("± loss",cps_loss_var,4)])
    _mr(f,[("hold min s",hold_min_var,5),("hold max s",hold_max_var,5)])
    _mr(f,[("burst %",burst_chance_var,4),("burst min s",burst_min_var,5)])
    _mr(f,[("burst max s",burst_max_var,5),("slip",slip_var,5)])

    # advanced toggle
    adv_var=tk.BooleanVar(value=False)
    adv_frame=tk.Frame(f,bg=T("bg2")); _reg(adv_frame,"bg","bg2")

    def _tog_adv():
        if adv_var.get(): adv_frame.pack(fill="x",padx=6,pady=1)
        else: adv_frame.pack_forget()

    adv_chk=tk.Checkbutton(f,text="Advanced (CPS clamp)",variable=adv_var,command=_tog_adv,
                            bg=T("bg2"),fg=T("fg3"),selectcolor=T("bg3"),
                            activebackground=T("bg2"),activeforeground=T("fg3"),
                            font=("Helvetica",7),anchor="w",relief="flat",bd=0)
    _reg(adv_chk,"bg","bg2"); adv_chk.pack(fill="x",padx=6,pady=(2,0))

    # advanced content
    tk.Label(adv_frame,text="Hard clamp so CPS never goes out of range:",
             bg=T("bg2"),fg=T("fg3"),font=("Helvetica",7),anchor="w"
             ).pack(fill="x")
    ar=tk.Frame(adv_frame,bg=T("bg2")); _reg(ar,"bg","bg2"); ar.pack(fill="x")
    for lbl,var in [("CPS min",cps_min_var),("CPS max",cps_max_var)]:
        tk.Label(ar,text=lbl,bg=T("bg2"),fg=T("fg2"),font=("Helvetica",8)).pack(side="left")
        We(ar,var,4,"bg3").pack(side="left",padx=(2,10))

    # tips
    tip=tk.Label(f,text="hold=press dur  burst=hesitation pause  loss=CPS variance  slip=missed click",
                 font=("Helvetica",7),bg=T("bg2"),fg=T("fg3"),
                 justify="left",anchor="w",wraplength=240)
    _reg(tip,"bg","bg2");_reg(tip,"fg","fg3"); tip.pack(fill="x",padx=6,pady=(2,0))

    # defaults button
    def _reset_clicker():
        D=settings.DEFAULTS
        for var,key in [(cps_base_var,"clicker_cps_base"),(cps_loss_var,"clicker_cps_loss"),
                        (cps_min_var,"clicker_cps_min"),(cps_max_var,"clicker_cps_max"),
                        (hold_min_var,"clicker_hold_min"),(hold_max_var,"clicker_hold_max"),
                        (burst_chance_var,"clicker_burst_chance"),(burst_min_var,"clicker_burst_min"),
                        (burst_max_var,"clicker_burst_max"),(slip_var,"clicker_slip_chance")]:
            var.set(str(D[key]))
    tk.Button(f,text="Reset defaults",command=_reset_clicker,
              bg=T("bg2"),fg=T("fg3"),activebackground=T("bg3"),
              relief="flat",font=("Helvetica",7),cursor="hand2",bd=0
              ).pack(anchor="e",padx=6,pady=(0,6))

_hm_layout=Wf(hb); _hm_layout.pack(fill="x")

def _rebuild_human_layout():
    for w in _hm_layout.winfo_children(): w.destroy()
    if settings.get("layout")=="horizontal":
        lc=Wf(_hm_layout); rc=Wf(_hm_layout)
        lc.pack(side="left",fill="both",expand=True)
        rc.pack(side="left",fill="both",expand=True)
        _build_delay(lc); _build_smooth(lc)
        _build_jitter(rc); _build_clicker(rc)
    else:
        _build_delay(_hm_layout); _build_smooth(_hm_layout)
        _build_jitter(_hm_layout); _build_clicker(_hm_layout)

_rebuild_human_layout()
Wsep(_inner)

# ══════════════════════════════════════════════════════════════════════════════
#  PRESETS
# ══════════════════════════════════════════════════════════════════════════════
sec_ps=Section(_inner,"Presets  💾","sec_presets")
pb2=sec_ps.body
pm_var=tk.StringVar(value=settings.get("preset_mode"))
pmr=Wf(pb2); pmr.pack(fill="x",pady=(0,6))
Wl(pmr,"Mode:",ck="fg2").pack(side="left")
for label,val in [("Simple","simple"),("Power","power")]:
    def _pm(v=val): pm_var.set(v); settings.set("preset_mode",v); _refresh_preset_ui()
    Wrb(pmr,label,pm_var,val,cmd=_pm,bk="bg",sz=9).pack(side="left",padx=6)

nr=Wf(pb2); nr.pack(fill="x",pady=2)
Wl(nr,"Name:").pack(side="left")
preset_name_var=tk.StringVar()
We(nr,preset_name_var,16).pack(side="left",padx=(4,0))
size_lbl=tk.Label(pb2,text="",font=("Helvetica",8),bg=T("bg"),fg=T("fg3"),
                  anchor="w",wraplength=280,justify="left")
_reg(size_lbl,"bg","bg");_reg(size_lbl,"fg","fg3"); size_lbl.pack(fill="x",pady=(2,0))

sr=Wf(pb2); sr.pack(fill="x",pady=4)
def _save_ia():
    name=preset_name_var.get().strip()
    if not name: set_status("error","enter a name"); return
    warn=presets.save_inapp(name,state.events)
    size_lbl.config(text=warn); set_status("saved",f"'{name}' in-app"); _refresh_load_list()
def _save_json():
    name=preset_name_var.get().strip()
    if not name: set_status("error","enter a name"); return
    folder=filedialog.askdirectory(title="Save to folder") if settings.get("preset_mode")=="power" else None
    if settings.get("preset_mode")=="power" and not folder: return
    path,sz=presets.save_json(name,state.events,folder)
    size_lbl.config(text=f"Saved {sz} → {path}"); set_status("saved",f"'{name}' .json")
def _save_gz():
    name=preset_name_var.get().strip()
    if not name: set_status("error","enter a name"); return
    folder=filedialog.askdirectory(title="Save to folder") if settings.get("preset_mode")=="power" else None
    if settings.get("preset_mode")=="power" and not folder: return
    path,sz,ratio=presets.save_gz(name,state.events,folder)
    size_lbl.config(text=f"Saved {sz} compressed {ratio} → {path}"); set_status("saved",f"'{name}' .gz")
Wb(sr,"Save in-app",_save_ia,padx=4,pady=4).pack(side="left",padx=(0,3))
Wb(sr,"Save .json", _save_json,padx=4,pady=4).pack(side="left",padx=(0,3))
Wb(sr,"Save .gz",   _save_gz,padx=4,pady=4).pack(side="left")
Wsep(pb2)

lhr=Wf(pb2); lhr.pack(fill="x")
Wl(lhr,"Saved presets:",ck="fg2").pack(side="left")
def _import():
    path=filedialog.askopenfilename(title="Import preset",
         filetypes=[("TaskLight","*.json *.tljson.gz"),("All","*.*")])
    if not path: return
    try:
        evts=presets.load_file(path); state.events=evts
        set_status("idle",f"loaded {len(evts)} events")
    except Exception as e: set_status("error",str(e))
Wb(lhr,"Import file…",_import,padx=4,pady=2).pack(side="right")

lf=Wf(pb2); lf.pack(fill="x",pady=4)
preset_lb=tk.Listbox(lf,height=5,bg=T("bg2"),fg=T("fg"),selectbackground=T("accent"),
                     selectforeground=T("bg"),font=("Helvetica",9),relief="flat",bd=0,
                     highlightthickness=1,highlightbackground=T("bg3"))
_reg(preset_lb,"bg","bg2");_reg(preset_lb,"fg","fg");_reg(preset_lb,"selectbackground","accent")
_reg(preset_lb,"highlightbackground","bg3")
preset_lb.pack(side="left",fill="both",expand=True)
ttk.Scrollbar(lf,orient="vertical",command=preset_lb.yview).pack(side="right",fill="y")
_load_items=[]

def _refresh_load_list():
    global _load_items; preset_lb.delete(0,"end"); _load_items=[]
    for name in presets.list_inapp():
        _load_items.append((name,"inapp","inapp"))
        preset_lb.insert("end",f"📦 {name}  [in-app]")
    for name,path,sz,fmt in presets.list_files():
        icon="🗜" if fmt=="gz" else "📄"
        _load_items.append((name,path,fmt))
        preset_lb.insert("end",f"{icon} {name}  ({sz})")

def _load_sel():
    sel=preset_lb.curselection()
    if not sel: return
    name,path,fmt=_load_items[sel[0]]
    try:
        evts=presets.load_inapp(name) if fmt=="inapp" else presets.load_file(path)
        state.events=evts; state.current_preset_name=name
        preset_name_var.set(name); set_status("idle",f"loaded '{name}' ({len(evts)} events)")
    except Exception as e: set_status("error",str(e))

def _del_sel():
    sel=preset_lb.curselection()
    if not sel: return
    name,path,fmt=_load_items[sel[0]]
    if not messagebox.askyesno("Delete",f"Delete preset '{name}'?"): return
    if fmt=="inapp": presets.delete_inapp(name)
    else:
        try: os.remove(path)
        except: pass
    _refresh_load_list()

lbr=Wf(pb2); lbr.pack(fill="x",pady=2)
Wb(lbr,"Load",_load_sel,padx=6,pady=3).pack(side="left",padx=(0,3))
Wb(lbr,"Delete",_del_sel,padx=6,pady=3,fg="red").pack(side="left")
Wb(lbr,"⟳ Refresh",_refresh_load_list,padx=6,pady=3).pack(side="right")

ar=Wf(pb2); ar.pack(fill="x",pady=(6,2))
Wl(ar,"Auto-load:",ck="fg2").pack(side="left")
auto_var=tk.StringVar(value=settings.get("auto_load_preset"))
We(ar,auto_var,14).pack(side="left",padx=(4,0))
def _set_auto(): settings.set("auto_load_preset",auto_var.get().strip())
Wb(ar,"Set",_set_auto,padx=4,pady=2).pack(side="left",padx=4)

folder_row=Wf(pb2)
folder_var=tk.StringVar(value=settings.get("preset_folder"))
Wl(folder_row,"Folder:").pack(side="left")
We(folder_row,folder_var,18).pack(side="left",padx=(4,4))
def _browse(): d=filedialog.askdirectory(); folder_var.set(d) if d else None; settings.set("preset_folder",d) if d else None
Wb(folder_row,"Browse…",_browse,padx=4,pady=2).pack(side="left")

def _refresh_preset_ui():
    if settings.get("preset_mode")=="power": folder_row.pack(fill="x",pady=2)
    else: folder_row.pack_forget()
    _refresh_load_list()
_refresh_preset_ui()
Wsep(_inner)

# ══════════════════════════════════════════════════════════════════════════════
#  CLICK DUPLICATOR
# ══════════════════════════════════════════════════════════════════════════════
sec_dup=Section(_inner,"Click Duplicator","sec_playback")
db=sec_dup.body

dup_enabled_var =tk.BooleanVar(value=settings.get("dup_enabled"))
dup_addon_var   =tk.BooleanVar(value=settings.get("dup_addon"))
dup_count_var   =tk.StringVar(value=str(settings.get("dup_count")))
dup_gap_var     =tk.StringVar(value=str(settings.get("dup_gap_ms")))
dup_mode_var    =tk.StringVar(value=settings.get("dup_mode"))
dup_jitter_var  =tk.BooleanVar(value=settings.get("dup_use_jitter"))
dup_btn_var     =tk.StringVar(value=settings.get("dup_button") or "same")

dt=Wf(db); dt.pack(fill="x",pady=(0,4))
Wc(dt,"Enable duplicator",dup_enabled_var,sz=10).pack(side="left")

df=tk.Frame(db,bg=T("bg2"),highlightthickness=1,highlightbackground=T("bg3"))
_reg(df,"bg","bg2");_reg(df,"highlightbackground","bg3"); df.pack(fill="x",pady=2)

tk.Label(df,text="When you click → fires N extra clicks in the gap before next click",
         bg=T("bg2"),fg=T("fg3"),font=("Helvetica",7),anchor="w",wraplength=260
         ).pack(fill="x",padx=6,pady=(4,2))

# addon/solo row
dms=Wf(df); dms.config(bg=T("bg2")); _reg(dms,"bg","bg2"); dms.pack(fill="x",padx=6,pady=1)
Wc(dms,"Addon (playback)",dup_addon_var,bk="bg2").pack(side="left")
hk_dup=(settings.get("hk_dup_solo") or "f4").upper()
dup_sv=tk.BooleanVar(value=_ds.solo_active)
def _dt(): duplicator.toggle_solo(); _refresh_mini()
Wc(dms,f"Solo [{hk_dup}]",dup_sv,cmd=_dt,bk="bg2").pack(side="left",padx=(8,0))

# settings rows
def _dr(pairs):
    f=tk.Frame(df,bg=T("bg2")); _reg(f,"bg","bg2"); f.pack(fill="x",padx=6,pady=1)
    for lbl,var,w in pairs:
        tk.Label(f,text=lbl,bg=T("bg2"),fg=T("fg2"),font=("Helvetica",8)).pack(side="left")
        We(f,var,w,"bg3").pack(side="left",padx=(2,10))

_dr([("Extra clicks (1-4)",dup_count_var,3),("Gap ms",dup_gap_var,5)])

# timing mode
tm=tk.Frame(df,bg=T("bg2")); _reg(tm,"bg","bg2"); tm.pack(fill="x",padx=6,pady=1)
tk.Label(tm,text="Timing:",bg=T("bg2"),fg=T("fg2"),font=("Helvetica",8)).pack(side="left")
for label,val in [("Random (default)","random"),("Even spacing","even")]:
    tk.Radiobutton(tm,text=label,variable=dup_mode_var,value=val,
                   bg=T("bg2"),fg=T("fg"),selectcolor=T("bg3"),
                   activebackground=T("bg2"),activeforeground=T("fg"),
                   font=("Helvetica",8),relief="flat").pack(side="left",padx=(4,0))

Wc(df,"Inherit jitter on duplicated clicks",dup_jitter_var,bk="bg2").pack(anchor="w",padx=6,pady=(2,0))

# button selector
btr=tk.Frame(df,bg=T("bg2")); _reg(btr,"bg","bg2"); btr.pack(fill="x",padx=6,pady=(2,0))
tk.Label(btr,text="Button:",bg=T("bg2"),fg=T("fg2"),font=("Helvetica",8)).pack(side="left")
for label,val in [("Same","same"),("Left","left"),("Right","right"),("Both","both")]:
    Wrb(btr,label,dup_btn_var,val,
        cmd=lambda: settings.set("dup_button",dup_btn_var.get())
        ).pack(side="left",padx=(4,0))

def _reset_dup():
    D=settings.DEFAULTS
    dup_count_var.set(str(D["dup_count"])); dup_gap_var.set(str(D["dup_gap_ms"]))
    dup_mode_var.set(D["dup_mode"]); dup_jitter_var.set(D["dup_use_jitter"])
tk.Button(df,text="Reset defaults",command=_reset_dup,bg=T("bg2"),fg=T("fg3"),
          activebackground=T("bg3"),relief="flat",font=("Helvetica",7),
          cursor="hand2",bd=0).pack(anchor="e",padx=6,pady=(0,6))

Wsep(_inner)

# ══════════════════════════════════════════════════════════════════════════════
#  FPS MONITOR
# ══════════════════════════════════════════════════════════════════════════════
sec_fps=Section(_inner,"FPS Monitor  🎮","sec_presets")
fb=sec_fps.body

fps_show_mini_var  =tk.BooleanVar(value=settings.get("fps_show_mini"))
fps_prefer_gpu_var =tk.BooleanVar(value=settings.get("fps_prefer_gpu"))
fps_region_var     =tk.StringVar(value="Full screen")  # display only

ff=tk.Frame(fb,bg=T("bg2"),highlightthickness=1,highlightbackground=T("bg3"))
_reg(ff,"bg","bg2");_reg(ff,"highlightbackground","bg3"); ff.pack(fill="x",pady=2)

tk.Label(ff,text="Measures visible frame changes in a screen region.",
         bg=T("bg2"),fg=T("fg3"),font=("Helvetica",7),anchor="w",wraplength=260
         ).pack(fill="x",padx=6,pady=(4,2))

# region selector
fr_row=tk.Frame(ff,bg=T("bg2")); _reg(fr_row,"bg","bg2"); fr_row.pack(fill="x",padx=6,pady=2)
tk.Label(fr_row,text="Region:",bg=T("bg2"),fg=T("fg2"),font=("Helvetica",8)).pack(side="left")
fps_region_lbl=tk.Label(fr_row,textvariable=fps_region_var,
                         bg=T("bg2"),fg=T("accent"),font=("Helvetica",8))
_reg(fps_region_lbl,"bg","bg2");_reg(fps_region_lbl,"fg","accent")
fps_region_lbl.pack(side="left",padx=(4,0))

_fps_region=[None]  # [x,y,w,h] or None

def _select_region():
    """Open transparent overlay for region drag-select."""
    overlay=tk.Toplevel()
    overlay.attributes("-fullscreen",True)
    overlay.attributes("-alpha",0.3)
    overlay.attributes("-topmost",True)
    overlay.configure(bg="black")
    overlay.title("Drag to select FPS region — release to confirm")

    canvas=tk.Canvas(overlay,bg="black",cursor="crosshair",
                     highlightthickness=0)
    canvas.pack(fill="both",expand=True)

    _start=[0,0]; _rect=[None]

    def on_press(e):
        _start[0]=e.x; _start[1]=e.y
        if _rect[0]: canvas.delete(_rect[0])

    def on_drag(e):
        if _rect[0]: canvas.delete(_rect[0])
        _rect[0]=canvas.create_rectangle(_start[0],_start[1],e.x,e.y,
                                          outline="#4a8fc4",width=2,fill="")

    def on_release(e):
        x1,y1=min(_start[0],e.x),min(_start[1],e.y)
        x2,y2=max(_start[0],e.x),max(_start[1],e.y)
        w,h=x2-x1,y2-y1
        if w>20 and h>20:
            _fps_region[0]=[x1,y1,w,h]
            fps_region_var.set(f"{w}×{h} at ({x1},{y1})")
        else:
            _fps_region[0]=None
            fps_region_var.set("Full screen")
        overlay.destroy()

    canvas.bind("<ButtonPress-1>",on_press)
    canvas.bind("<B1-Motion>",on_drag)
    canvas.bind("<ButtonRelease-1>",on_release)
    overlay.bind("<Escape>",lambda e: overlay.destroy())

def _use_fullscreen():
    _fps_region[0]=None; fps_region_var.set("Full screen")

tk.Button(fr_row,text="Select region",command=_select_region,
          bg=T("bg3"),fg=T("fg"),activebackground=T("bg4"),
          relief="flat",font=("Helvetica",8),cursor="hand2",padx=6,pady=2
          ).pack(side="left",padx=(8,3))
tk.Button(fr_row,text="Full screen",command=_use_fullscreen,
          bg=T("bg3"),fg=T("fg"),activebackground=T("bg4"),
          relief="flat",font=("Helvetica",8),cursor="hand2",padx=6,pady=2
          ).pack(side="left")

# options
fo=tk.Frame(ff,bg=T("bg2")); _reg(fo,"bg","bg2"); fo.pack(fill="x",padx=6,pady=2)
Wc(fo,"Prefer GPU query if available",fps_prefer_gpu_var,bk="bg2").pack(side="left")
Wc(fo,"Show in mini mode",fps_show_mini_var,bk="bg2").pack(side="left",padx=(10,0))

# stats
fps_stats_var=tk.StringVar(value="cur: --   min: --   avg: --   max: --")
fps_stats_lbl=tk.Label(ff,textvariable=fps_stats_var,bg=T("bg2"),fg=T("accent"),
                        font=("Courier",9),anchor="w")
_reg(fps_stats_lbl,"bg","bg2");_reg(fps_stats_lbl,"fg","accent")
fps_stats_lbl.pack(fill="x",padx=6,pady=2)

fps_method_lbl=tk.Label(ff,text="",bg=T("bg2"),fg=T("fg3"),font=("Helvetica",7),anchor="w")
_reg(fps_method_lbl,"bg","bg2"); fps_method_lbl.pack(fill="x",padx=6)

# sparkline
fps_spark=tk.Canvas(ff,bg=T("bg3"),height=48,highlightthickness=0,bd=0)
_reg(fps_spark,"bg","bg3"); fps_spark.pack(fill="x",padx=6,pady=(0,4))

fps_ind=tk.Label(ff,text="⬤ Inactive",bg=T("bg2"),fg=T("fg3"),font=("Helvetica",8),anchor="w")
_reg(fps_ind,"bg","bg2"); fps_ind.pack(fill="x",padx=6)

def _update_fps_ui():
    if not _fs2.active: return
    cur=_fs2.current; mn=_fs2.minimum; av=_fs2.avg; mx=_fs2.maximum
    def _f(v): return f"{v:.1f}" if v is not None else "--"
    fps_stats_var.set(f"cur:{_f(cur)}   min:{_f(mn)}   avg:{_f(av)}   max:{_f(mx)}")
    fps_method_lbl.config(text=f"method: {_fs2.method}")

    h=_fs2.history; cw=fps_spark.winfo_width() or 270; ch=48
    fps_spark.delete("all")
    valid=[x for x in h if x is not None]
    if valid:
        lo,hi=min(valid),max(valid); rng=max(hi-lo,1.0)
        step=cw/max(len(h)-1,1)
        pts=[(int(i*step),int(ch-((v-lo)/rng*(ch-6))-3)) for i,v in enumerate(h) if v]
        for i in range(len(pts)-1):
            fps_spark.create_line(pts[i][0],pts[i][1],pts[i+1][0],pts[i+1][1],
                                  fill=T("green"),width=1)
        if cur: fps_spark.create_text(cw-4,4,text=f"{cur:.0f}fps",
                                       fill=T("accent"),font=("Helvetica",8),anchor="ne")
    _refresh_mini()
    fps_spark.after(1000,_update_fps_ui)

fbr=tk.Frame(ff,bg=T("bg2")); _reg(fbr,"bg","bg2"); fbr.pack(fill="x",padx=6,pady=(0,8))

def _toggle_fps():
    if not _fs2.active:
        fps.start_monitor(region=_fps_region[0] or None,
                          prefer_gpu=fps_prefer_gpu_var.get())
        fps_btn.config(text="Stop FPS Monitor")
        fps_ind.config(text="⬤ Active",fg=T("green"))
        _update_fps_ui()
    else:
        fps.stop_monitor()
        fps_btn.config(text="Start FPS Monitor")
        fps_ind.config(text="⬤ Inactive",fg=T("fg3"))
        fps_stats_var.set("cur: --   min: --   avg: --   max: --")
        fps_spark.delete("all")
    _refresh_mini()

fps_btn=tk.Button(fbr,text="Start FPS Monitor",command=_toggle_fps,
                  bg=T("bg3"),fg=T("fg"),activebackground=T("bg4"),
                  relief="flat",font=("Helvetica",9,"bold"),cursor="hand2",padx=8,pady=4)
_reg(fps_btn,"bg","bg3");_reg(fps_btn,"fg","fg");_reg(fps_btn,"activebackground","bg4")
fps_btn.pack(side="left")

tk.Label(fbr,text="Tip: smaller region = less CPU",
         bg=T("bg2"),fg=T("fg3"),font=("Helvetica",7)).pack(side="left",padx=(10,0))

Wsep(_inner)

# ══════════════════════════════════════════════════════════════════════════════
#  NETWORK EXTRAS
# ══════════════════════════════════════════════════════════════════════════════
sec_net=Section(_inner,"Extras — Network","sec_network")
nb=sec_net.body

host_var=tk.StringVar(value=settings.get("net_ping_host") or "8.8.8.8")
show_mini_ping_var=tk.BooleanVar(value=settings.get("net_show_mini_ping"))

# not-ready panel
_net_nr=tk.Frame(nb,bg=T("bg2"),padx=10,pady=8); _reg(_net_nr,"bg","bg2")
_net_nr.pack(fill="x",pady=2)
tk.Label(_net_nr,text="⚙  Click 'Set up' to enable network features.",
         bg=T("bg2"),fg=T("fg2"),font=("Helvetica",9),
         wraplength=270,justify="left",anchor="w").pack(fill="x")

# ready panel
_net_rdy=tk.Frame(nb,bg=T("bg")); _reg(_net_rdy,"bg","bg")

# iface display row
ifr=tk.Frame(_net_rdy,bg=T("bg")); _reg(ifr,"bg","bg"); ifr.pack(fill="x",pady=2)
tk.Label(ifr,text="Interface:",bg=T("bg"),fg=T("fg2"),font=("Helvetica",9)).pack(side="left")
iface_lbl=tk.Label(ifr,textvariable=_iface_var,bg=T("bg"),fg=T("accent"),font=("Helvetica",9,"bold"))
_reg(iface_lbl,"bg","bg");_reg(iface_lbl,"fg","accent"); iface_lbl.pack(side="left",padx=(4,0))

def _nf(p,title,color):
    f=tk.Frame(p,bg=T("bg2"),highlightthickness=1,highlightbackground=T("bg3"))
    _reg(f,"bg","bg2");_reg(f,"highlightbackground","bg3"); f.pack(fill="x",pady=2)
    tk.Label(f,text=title,font=("Helvetica",9,"bold"),bg=T("bg2"),fg=T(color),anchor="w"
             ).pack(fill="x",padx=6,pady=(4,2))
    return f

def _ne(p,var,w=5):
    e=tk.Entry(p,textvariable=var,width=w,bg=T("bg3"),fg=T("fg"),
               insertbackground=T("fg"),relief="flat",font=("Helvetica",9),
               highlightthickness=1,highlightbackground=T("bg3"))
    _reg(e,"bg","bg3");_reg(e,"fg","fg"); return e

def _nr2(p,pairs):
    f=tk.Frame(p,bg=T("bg2")); _reg(f,"bg","bg2"); f.pack(fill="x",padx=8,pady=1)
    for lbl,var,w in pairs:
        tk.Label(f,text=lbl,bg=T("bg2"),fg=T("fg2"),font=("Helvetica",8)).pack(side="left")
        _ne(f,var,w).pack(side="left",padx=(2,10))

# ── Limiter ───────────────────────────────────────────────────────────────────
lp=_nf(_net_rdy,"Ping Limiter","accent")
delay_ms_var =tk.StringVar(value="100")
delay_ms_loss=tk.StringVar(value="20")
pkt_loss_v   =tk.StringVar(value="0")
pkt_loss_lv  =tk.StringVar(value="2")
_nr2(lp,[("Base ms",delay_ms_var,5),("± ms",delay_ms_loss,5)])
_nr2(lp,[("Pkt loss %",pkt_loss_v,5),("± %",pkt_loss_lv,5)])
lim_ind=tk.Label(lp,text="⬤ Inactive",bg=T("bg2"),fg=T("fg3"),font=("Helvetica",8),anchor="w")
_reg(lim_ind,"bg","bg2"); lim_ind.pack(fill="x",padx=8)
lim_err=tk.Label(lp,text="",bg=T("bg2"),fg=T("red"),font=("Helvetica",8),anchor="w",wraplength=270)
_reg(lim_err,"bg","bg2"); lim_err.pack(fill="x",padx=8)

def _toggle_lim():
    iface=_iface_var.get()
    if not _ns.limiter_active:
        try: d=int(delay_ms_var.get()); dl=int(delay_ms_loss.get()); pl=float(pkt_loss_v.get())
        except: lim_err.config(text="Invalid values"); return
        ok,err=network.apply_limiter(iface,d,dl,pl)
        if ok:
            lim_ind.config(text=f"⬤ Active  {d}ms ±{dl}ms  loss:{pl}%",fg=T("green"))
            lim_btn.config(text="Stop Limiter"); lim_err.config(text="")
        else: lim_err.config(text=f"Error: {err}"); _ns.limiter_active=False
    else:
        network.stop_limiter(iface)
        lim_ind.config(text="⬤ Inactive",fg=T("fg3")); lim_btn.config(text="Start Limiter")

lim_btn=tk.Button(lp,text="Start Limiter",command=_toggle_lim,
                  bg=T("bg3"),fg=T("fg"),activebackground=T("bg4"),
                  relief="flat",font=("Helvetica",9,"bold"),cursor="hand2",padx=8,pady=4)
_reg(lim_btn,"bg","bg3");_reg(lim_btn,"fg","fg");_reg(lim_btn,"activebackground","bg4")
lim_btn.pack(anchor="w",padx=8,pady=(4,8))

# ── Blocker ───────────────────────────────────────────────────────────────────
blkp=_nf(_net_rdy,"Packet Blocker","red")
hk_blk=(settings.get("hk_net_blocker") or "f3").upper()
tk.Label(blkp,text=f"Drops 100% of outbound traffic. Hotkey: {hk_blk}  Shown in mini mode.",
         bg=T("bg2"),fg=T("fg3"),font=("Helvetica",8),anchor="w",wraplength=270
         ).pack(fill="x",padx=8)
blk_ind=tk.Label(blkp,text="⬤ Inactive",bg=T("bg2"),fg=T("fg3"),font=("Helvetica",8),anchor="w")
_reg(blk_ind,"bg","bg2"); blk_ind.pack(fill="x",padx=8)
blk_err=tk.Label(blkp,text="",bg=T("bg2"),fg=T("red"),font=("Helvetica",8),anchor="w",wraplength=270)
_reg(blk_err,"bg","bg2"); blk_err.pack(fill="x",padx=8)

def _refresh_blocker_ui():
    if _ns.blocker_active:
        blk_ind.config(text="⬤ BLOCKED — all outbound traffic dropped",fg=T("red"))
        blk_btn.config(text="Unblock Traffic",fg=T("green"))
    else:
        blk_ind.config(text="⬤ Inactive",fg=T("fg3"))
        blk_btn.config(text="Block Traffic",fg=T("fg"))

def _toggle_blk():
    iface=_iface_var.get()
    if not _ns.blocker_active:
        ok,err=network.apply_blocker(iface)
        if ok: blk_err.config(text="")
        else:  blk_err.config(text=f"Error: {err}"); _ns.blocker_active=False
    else: network.stop_blocker(iface)
    _refresh_blocker_ui(); _refresh_mini()

blk_btn=tk.Button(blkp,text="Block Traffic",command=_toggle_blk,
                  bg=T("bg3"),fg=T("fg"),activebackground=T("bg4"),
                  relief="flat",font=("Helvetica",9,"bold"),cursor="hand2",padx=8,pady=4)
_reg(blk_btn,"bg","bg3");_reg(blk_btn,"fg","fg");_reg(blk_btn,"activebackground","bg4")
blk_btn.pack(anchor="w",padx=8,pady=(4,8))

# ── Ping Monitor ──────────────────────────────────────────────────────────────
monp=_nf(_net_rdy,"Ping Monitor","green")
hr=tk.Frame(monp,bg=T("bg2")); _reg(hr,"bg","bg2"); hr.pack(fill="x",padx=8,pady=2)
tk.Label(hr,text="Host:",bg=T("bg2"),fg=T("fg2"),font=("Helvetica",8)).pack(side="left")
_ne(hr,host_var,16).pack(side="left",padx=(4,0))

stats_var=tk.StringVar(value="cur: --   min: --   avg: --   max: --")
stats_lbl=tk.Label(monp,textvariable=stats_var,bg=T("bg2"),fg=T("accent"),
                   font=("Courier",9),anchor="w")
_reg(stats_lbl,"bg","bg2");_reg(stats_lbl,"fg","accent")
stats_lbl.pack(fill="x",padx=8,pady=2)

spark=tk.Canvas(monp,bg=T("bg3"),height=48,highlightthickness=0,bd=0)
_reg(spark,"bg","bg3"); spark.pack(fill="x",padx=8,pady=(0,4))

mon_ind=tk.Label(monp,text="⬤ Inactive",bg=T("bg2"),fg=T("fg3"),font=("Helvetica",8),anchor="w")
_reg(mon_ind,"bg","bg2"); mon_ind.pack(fill="x",padx=8)

def _update_mon():
    if not _ns.monitor_active: return
    rtt=_ns.ping_current; mn=_ns.ping_min; av=_ns.ping_avg; mx=_ns.ping_max
    def _fmt(v): return f"{v:.0f}" if v is not None else "--"
    stats_var.set(f"cur:{_fmt(rtt)}ms   min:{_fmt(mn)}   avg:{_fmt(av)}   max:{_fmt(mx)}")
    # sparkline
    h=_ns.ping_history; cw=spark.winfo_width() or 270; ch=48
    spark.delete("all")
    valid=[x for x in h if x is not None]
    if valid:
        lo,hi=min(valid),max(valid); rng=max(hi-lo,1.0)
        step=cw/max(len(h)-1,1)
        pts=[]
        for i,v in enumerate(h):
            x=int(i*step)
            y=int(ch-((v-lo)/rng*(ch-6))-3) if v is not None else ch-1
            pts.append((x,y))
        for i in range(len(pts)-1):
            col=T("blue") if h[i] is not None else T("fg3")
            spark.create_line(pts[i][0],pts[i][1],pts[i+1][0],pts[i+1][1],fill=col,width=1)
        # current RTT text
        if rtt is not None:
            spark.create_text(cw-4,4,text=f"{rtt:.0f}ms",fill=T("accent"),
                              font=("Helvetica",8),anchor="ne")
    _refresh_mini()
    spark.after(1000,_update_mon)

mrr=tk.Frame(monp,bg=T("bg2")); _reg(mrr,"bg","bg2"); mrr.pack(fill="x",padx=8,pady=(0,8))

def _toggle_mon():
    if not _ns.monitor_active:
        network.start_monitor(host=host_var.get())
        mon_btn.config(text="Stop Monitor"); mon_ind.config(text="⬤ Active",fg=T("green"))
        _update_mon()
    else:
        network.stop_monitor(); mon_btn.config(text="Start Monitor")
        stats_var.set("cur: --   min: --   avg: --   max: --")
        spark.delete("all"); mon_ind.config(text="⬤ Inactive",fg=T("fg3"))
    _refresh_mini()

mon_btn=tk.Button(mrr,text="Start Monitor",command=_toggle_mon,
                  bg=T("bg3"),fg=T("fg"),activebackground=T("bg4"),
                  relief="flat",font=("Helvetica",9,"bold"),cursor="hand2",padx=8,pady=4)
_reg(mon_btn,"bg","bg3");_reg(mon_btn,"fg","fg");_reg(mon_btn,"activebackground","bg4")
mon_btn.pack(side="left")
Wc(mrr,"Show in mini mode",show_mini_ping_var,bk="bg2").pack(side="left",padx=(10,0))

# ── setup dialog ──────────────────────────────────────────────────────────────
def _open_setup():
    win=tk.Toplevel(); win.title("Network Setup"); win.configure(bg=T("bg"))
    win.attributes("-topmost",True); win.resizable(True,True); win.geometry("500x560")

    tk.Label(win,text="Scanning…",bg=T("bg"),fg=T("fg2"),font=("Helvetica",9)).pack(pady=10)
    win.update(); info=network.check_setup()
    for w in win.winfo_children(): w.destroy()

    tk.Label(win,text="Network Extras Setup",font=("Helvetica",12,"bold"),
             bg=T("bg"),fg=T("fg")).pack(pady=(10,4))

    st=tk.Frame(win,bg=T("bg")); st.pack(fill="x",padx=16,pady=2)
    ok_c=T("green"); bad_c=T("red"); warn_c=T("orange")
    tk.Label(st,text=f"OS: {info['os'].title()}",bg=T("bg"),fg=T("fg2"),
             font=("Helvetica",9)).pack(side="left")
    if info["os"]=="linux":
        for txt,ok in [(f"  tc: {'✓' if info['tc_available'] else '✗'}",info["tc_available"]),
                       (f"  sudo: {'✓' if info['is_admin'] else '⚠ needed'}",info["is_admin"])]:
            tk.Label(st,text=txt,bg=T("bg"),fg=(ok_c if ok else warn_c),
                     font=("Helvetica",9)).pack(side="left")
    else:
        for txt,ok in [(f"  clumsy: {'✓' if info['clumsy_available'] else '✗'}",info["clumsy_available"]),
                       (f"  admin: {'✓' if info['is_admin'] else '✗'}",info["is_admin"])]:
            tk.Label(st,text=txt,bg=T("bg"),fg=(ok_c if ok else bad_c),
                     font=("Helvetica",9)).pack(side="left")

    tk.Frame(win,bg=T("sep"),height=1).pack(fill="x",padx=16,pady=8)
    tk.Label(win,text="Select interface:",bg=T("bg"),fg=T("fg2"),
             font=("Helvetica",9,"bold")).pack(anchor="w",padx=16)

    sel_var=tk.StringVar(value=_iface_var.get() or info["default_iface"])
    for name,is_def,ip in info["interfaces"]:
        lbl=f"  {name}"
        if ip: lbl+=f"  ({ip})"
        if is_def: lbl+="  ← default, recommended"
        tk.Radiobutton(win,text=lbl,variable=sel_var,value=name,
                       bg=T("bg"),fg=T("fg"),selectcolor=T("bg2"),
                       activebackground=T("bg"),activeforeground=T("fg"),
                       font=("Helvetica",9),anchor="w",relief="flat"
                       ).pack(fill="x",padx=24,pady=1)

    ovr=tk.Frame(win,bg=T("bg")); ovr.pack(fill="x",padx=16,pady=2)
    tk.Label(ovr,text="Override:",bg=T("bg"),fg=T("fg3"),font=("Helvetica",8)).pack(side="left")
    ov_var=tk.StringVar()
    tk.Entry(ovr,textvariable=ov_var,width=14,bg=T("bg2"),fg=T("fg"),
             insertbackground=T("fg"),relief="flat",font=("Helvetica",9),
             highlightthickness=1,highlightbackground=T("bg3")).pack(side="left",padx=(4,0))

    tk.Frame(win,bg=T("sep"),height=1).pack(fill="x",padx=16,pady=8)
    tk.Label(win,text="Setup instructions:",bg=T("bg"),fg=T("fg2"),
             font=("Helvetica",9,"bold")).pack(anchor="w",padx=16)

    instr=tk.Frame(win,bg=T("bg2"),padx=10,pady=8); instr.pack(fill="x",padx=16,pady=4)
    for line in network.get_setup_instructions(info):
        mono=line.startswith("  ") and line.strip()
        tk.Label(instr,text=line,bg=T("bg2"),fg=(T("accent") if mono else T("fg2")),
                 font=("Courier" if mono else "Helvetica",8),
                 anchor="w",justify="left").pack(fill="x")

    auto_status=tk.Label(win,text="",bg=T("bg"),fg=T("fg2"),
                          font=("Helvetica",8),wraplength=440,justify="left")
    auto_status.pack(fill="x",padx=16)

    def _auto_setup():
        auto_status.config(text="Running setup via pkexec…",fg=T("orange"))
        win.update()
        ok,msg=network.run_auto_setup_linux()
        auto_status.config(text=msg,fg=(T("green") if ok else T("red")))

    btn_row2=tk.Frame(win,bg=T("bg")); btn_row2.pack(fill="x",padx=16,pady=8)

    if info["os"]=="linux":
        tk.Button(btn_row2,text="Run setup automatically (pkexec)",
                  command=_auto_setup,
                  bg=T("bg3"),fg=T("fg"),activebackground=T("bg4"),
                  relief="flat",font=("Helvetica",9),cursor="hand2",padx=8,pady=4
                  ).pack(side="left",padx=(0,8))

    def _confirm():
        iface=ov_var.get().strip() or sel_var.get()
        _iface_var.set(iface); _ns.interface=iface
        settings.set("net_iface",iface); _ns.setup_done=True
        win.destroy()
        _net_nr.pack_forget(); _net_rdy.pack(fill="x")
        setup_btn.config(text="⚙ Change interface")

    tk.Button(btn_row2,text="Confirm & Enable",command=_confirm,
              bg=T("accent"),fg=T("bg"),activebackground=T("blue"),
              activeforeground=T("bg"),relief="flat",
              font=("Helvetica",10,"bold"),cursor="hand2",padx=10,pady=6
              ).pack(side="left")

setup_btn=Wb(nb,"⚙ Set up",_open_setup,padx=6,pady=3)
setup_btn.pack(anchor="w",pady=(0,4))

# auto-restore if iface was saved
if settings.get("net_iface"):
    _ns.interface=settings.get("net_iface"); _ns.setup_done=True
    _net_nr.pack_forget(); _net_rdy.pack(fill="x")
    setup_btn.config(text="⚙ Change interface")

Wsep(_inner)

# ══════════════════════════════════════════════════════════════════════════════
#  SYSTEM MONITOR
# ══════════════════════════════════════════════════════════════════════════════
sec_sys=Section(_inner,"System Monitor  💻","sec_sysmon")
sb2=sec_sys.body

# vars
sysmon_enabled_var =tk.BooleanVar(value=settings.get("sysmon_enabled"))
sysmon_interval_var=tk.StringVar(value=settings.get("sysmon_interval"))
sysmon_cpu_var     =tk.BooleanVar(value=settings.get("sysmon_show_cpu"))
sysmon_ram_var     =tk.BooleanVar(value=settings.get("sysmon_show_ram"))
sysmon_gpu_var     =tk.BooleanVar(value=settings.get("sysmon_show_gpu"))
sysmon_disk_var    =tk.BooleanVar(value=settings.get("sysmon_show_disk"))
sysmon_net_var     =tk.BooleanVar(value=settings.get("sysmon_show_net"))
sysmon_temp_var    =tk.BooleanVar(value=settings.get("sysmon_show_temp"))
sysmon_mini_var    =tk.BooleanVar(value=settings.get("sysmon_show_mini"))
sysmon_cores_var   =tk.BooleanVar(value=settings.get("sysmon_show_cores"))

if not sysmon.PSUTIL_AVAILABLE:
    tk.Label(sb2,text="⚠  psutil not installed — run: pip install psutil",
             bg=T("bg"),fg=T("orange"),font=("Helvetica",9),anchor="w"
             ).pack(fill="x",pady=4)

# enable + interval row
et=Wf(sb2); et.pack(fill="x",pady=(0,4))
Wc(et,"Enable system monitor",sysmon_enabled_var,sz=10).pack(side="left")
Wl(et,"Interval s:").pack(side="left",padx=(14,4))
We(et,sysmon_interval_var,4).pack(side="left")

# metrics panel
sf=tk.Frame(sb2,bg=T("bg2"),highlightthickness=1,highlightbackground=T("bg3"))
_reg(sf,"bg","bg2");_reg(sf,"highlightbackground","bg3"); sf.pack(fill="x",pady=2)

tk.Label(sf,text="Visible metrics",font=("Helvetica",9,"bold"),
         bg=T("bg2"),fg=T("accent"),anchor="w").pack(fill="x",padx=8,pady=(6,4))

# metric toggles grid
mg=tk.Frame(sf,bg=T("bg2")); _reg(mg,"bg","bg2"); mg.pack(fill="x",padx=8,pady=(0,4))
metrics=[
    ("CPU %",       sysmon_cpu_var),  ("RAM %",      sysmon_ram_var),
    ("GPU %",       sysmon_gpu_var),  ("Disk %",     sysmon_disk_var),
    ("Net MB/s",sysmon_net_var),  ("Temperature",sysmon_temp_var),
    ("Per-core CPU",sysmon_cores_var),("Show in mini",sysmon_mini_var),
]
for i,(label,var) in enumerate(metrics):
    row,col=divmod(i,2)
    f=tk.Frame(mg,bg=T("bg2")); _reg(f,"bg","bg2")
    f.grid(row=row,column=col,sticky="w",padx=(0,16),pady=1)
    Wc(f,label,var,bk="bg2").pack(side="left")
mg.columnconfigure(0,weight=1); mg.columnconfigure(1,weight=1)

# live stats display
tk.Frame(sf,bg=T("bg3"),height=1).pack(fill="x",padx=8,pady=4)

def _make_bar(parent, label, color="accent"):
    """Returns (frame, label_var, bar_canvas, pct_var)"""
    f=tk.Frame(parent,bg=T("bg2")); _reg(f,"bg","bg2"); f.pack(fill="x",padx=8,pady=1)
    tk.Label(f,text=label,width=10,anchor="w",bg=T("bg2"),fg=T("fg2"),
             font=("Helvetica",8)).pack(side="left")
    canvas=tk.Canvas(f,bg=T("bg3"),height=12,highlightthickness=0,bd=0,width=140)
    _reg(canvas,"bg","bg3"); canvas.pack(side="left",padx=(4,6))
    pct_var=tk.StringVar(value="--")
    tk.Label(f,textvariable=pct_var,width=12,anchor="w",bg=T("bg2"),fg=T(color),
             font=("Courier",8)).pack(side="left")
    return canvas, pct_var

def _draw_bar(canvas, pct, color):
    canvas.delete("all")
    if pct is None: return
    w=canvas.winfo_width() or 140
    fill_w=int(w * pct / 100)
    # background
    canvas.create_rectangle(0,0,w,12,fill=T("bg3"),outline="")
    # fill — color based on level
    col=T("green") if pct<60 else (T("orange") if pct<85 else T("red"))
    if fill_w>0:
        canvas.create_rectangle(0,0,fill_w,12,fill=col,outline="")

cpu_canvas, cpu_pct_var = _make_bar(sf,"CPU")
ram_canvas, ram_pct_var = _make_bar(sf,"RAM")
gpu_canvas, gpu_pct_var = _make_bar(sf,"GPU","blue")
dsk_canvas, dsk_pct_var = _make_bar(sf,"Disk")

# extra info label (temp, net, vram)
extra_var=tk.StringVar(value="")
extra_lbl=tk.Label(sf,textvariable=extra_var,bg=T("bg2"),fg=T("fg2"),
                   font=("Courier",8),anchor="w",wraplength=260)
_reg(extra_lbl,"bg","bg2"); extra_lbl.pack(fill="x",padx=8,pady=(2,0))

# per-core row
cores_frame=tk.Frame(sf,bg=T("bg2")); _reg(cores_frame,"bg","bg2")
cores_frame.pack(fill="x",padx=8,pady=(2,0))
_core_labels=[]

sys_ind=tk.Label(sf,text="⬤ Inactive",bg=T("bg2"),fg=T("fg3"),
                  font=("Helvetica",8),anchor="w")
_reg(sys_ind,"bg","bg2"); sys_ind.pack(fill="x",padx=8,pady=(4,0))

def _update_sysmon_ui():
    if not _ss.active: return
    s=_ss

    # CPU
    if sysmon_cpu_var.get() and s.cpu_pct is not None:
        _draw_bar(cpu_canvas,s.cpu_pct,"green")
        t=f" {s.cpu_temp:.0f}°C" if sysmon_temp_var.get() and s.cpu_temp else ""
        cpu_pct_var.set(f"{s.cpu_pct:.1f}%{t}")
    else:
        cpu_pct_var.set("disabled")

    # RAM
    if sysmon_ram_var.get() and s.ram_pct is not None:
        _draw_bar(ram_canvas,s.ram_pct,"green")
        ram_pct_var.set(f"{s.ram_pct:.1f}%  {s.ram_used_gb}/{s.ram_total_gb}GB")
    else:
        ram_pct_var.set("disabled")

    # GPU
    if sysmon_gpu_var.get() and s.gpu_pct is not None:
        _draw_bar(gpu_canvas,s.gpu_pct,"blue")
        vr=f" VRAM:{s.gpu_vram_pct:.0f}%" if s.gpu_vram_pct else ""
        gt=f" {s.gpu_temp:.0f}°C" if sysmon_temp_var.get() and s.gpu_temp else ""
        gpu_pct_var.set(f"{s.gpu_pct:.1f}%{vr}{gt}")
    else:
        gpu_pct_var.set("no GPU" if s.gpu_pct is None else "disabled")

    # Disk
    if sysmon_disk_var.get() and s.disk_pct is not None:
        _draw_bar(dsk_canvas,s.disk_pct,"green")
        rio=f" R:{s.disk_read_mb:.1f}" if s.disk_read_mb else ""
        wio=f" W:{s.disk_write_mb:.1f}MB/s" if s.disk_write_mb else ""
        dsk_pct_var.set(f"{s.disk_pct:.1f}%{rio}{wio}")
    else:
        dsk_pct_var.set("disabled")

    # extra: network
    extras=[]
    if sysmon_net_var.get() and s.net_up_mb is not None:
        extras.append(f"Net ↑{s.net_up_mb:.2f} ↓{s.net_down_mb:.2f} MB/s")
    extra_var.set("  ".join(extras))

    # per-core
    if sysmon_cores_var.get() and s.cpu_per_core:
        for w in cores_frame.winfo_children(): w.destroy()
        _core_labels.clear()
        tk.Label(cores_frame,text="Cores:",bg=T("bg2"),fg=T("fg3"),
                 font=("Helvetica",7)).pack(side="left")
        for i,pct in enumerate(s.cpu_per_core[:16]):
            col=T("green") if pct<60 else (T("orange") if pct<85 else T("red"))
            l=tk.Label(cores_frame,text=f"{pct:.0f}",bg=T("bg2"),fg=col,
                       font=("Courier",7))
            l.pack(side="left",padx=1)
            _core_labels.append(l)

    _refresh_mini()
    sf.after(int(float(sysmon_interval_var.get() or "1")*1000), _update_sysmon_ui)

sbr=tk.Frame(sf,bg=T("bg2")); _reg(sbr,"bg","bg2")
sbr.pack(fill="x",padx=8,pady=(6,8))

def _toggle_sysmon():
    if not _ss.active:
        interval=float(sysmon_interval_var.get() or "1.0")
        sysmon.start(interval=interval)
        sys_btn.config(text="Stop Monitor")
        sys_ind.config(text="⬤ Active",fg=T("green"))
        _update_sysmon_ui()
    else:
        sysmon.stop()
        sys_btn.config(text="Start Monitor")
        sys_ind.config(text="⬤ Inactive",fg=T("fg3"))
        for c,v in [(cpu_canvas,cpu_pct_var),(ram_canvas,ram_pct_var),
                    (gpu_canvas,gpu_pct_var),(dsk_canvas,dsk_pct_var)]:
            c.delete("all"); v.set("--")
        extra_var.set(""); sys_mini_lbl.config(text="")

sys_btn=tk.Button(sbr,text="Start Monitor",command=_toggle_sysmon,
                  bg=T("bg3"),fg=T("fg"),activebackground=T("bg4"),
                  relief="flat",font=("Helvetica",9,"bold"),cursor="hand2",padx=8,pady=4)
_reg(sys_btn,"bg","bg3");_reg(sys_btn,"fg","fg");_reg(sys_btn,"activebackground","bg4")
sys_btn.pack(side="left")

if not sysmon.PSUTIL_AVAILABLE:
    tk.Label(sbr,text="pip install psutil",bg=T("bg2"),fg=T("orange"),
             font=("Courier",8)).pack(side="left",padx=(10,0))

Wsep(_inner)

# ══════════════════════════════════════════════════════════════════════════════
#  KEYBINDS
# ══════════════════════════════════════════════════════════════════════════════
sec_kb=Section(_inner,"Keybinds","sec_keybinds")
kbb=sec_kb.body
Wl(kbb,"Supports: f6  ctrl+alt+p  j  etc.",ck="fg3").pack(fill="x",pady=(0,4))
_KB_DEFS=[
    ("hk_quit","Quit"),("hk_record","Record"),("hk_play","Play"),("hk_stop","Stop"),
    ("hk_jitter_solo","Jitter solo"),("hk_clicker_solo","Clicker solo"),
    ("hk_net_blocker","Packet blocker"),
    ("hk_dup_solo","Click duplicator solo"),
]
_kb_vars={}
for key,label in _KB_DEFS:
    row=Wf(kbb); row.pack(fill="x",pady=1)
    tk.Label(row,text=label,width=18,anchor="w",bg=T("bg"),fg=T("fg2"),
             font=("Helvetica",9)).pack(side="left")
    var=tk.StringVar(value=settings.get(key))
    _kb_vars[key]=var; We(row,var,14).pack(side="left",padx=(4,0))
def _apply_kb():
    for k,v in _kb_vars.items():
        val=v.get().strip().lower()
        if val: settings.set(k,val)
    set_status("idle","keybinds saved")
Wb(kbb,"Apply keybinds",_apply_kb,pady=4).pack(pady=(6,2),anchor="w")
Wsep(_inner)

# ══════════════════════════════════════════════════════════════════════════════
#  WAYLAND BANNER
# ══════════════════════════════════════════════════════════════════════════════
xdg=os.environ.get("XDG_SESSION_TYPE","").lower()
if settings.get("wayland_banner") and (xdg=="wayland" or os.environ.get("WAYLAND_DISPLAY")):
    wf=tk.Frame(_inner,bg=T("bg2"),padx=10,pady=6); _reg(wf,"bg","bg2")
    wf.pack(fill="x",padx=10,pady=4)
    tk.Label(wf,text="⚠  Wayland detected — hotkeys only work inside the app window.",
             bg=T("bg2"),fg=T("orange"),font=("Helvetica",8,"bold"),
             anchor="w",wraplength=270,justify="left").pack(fill="x")
    tk.Label(wf,text="Login screen → gear → GNOME on Xorg  to switch to X11.",
             bg=T("bg2"),fg=T("fg2"),font=("Helvetica",8),
             anchor="w",wraplength=270,justify="left").pack(fill="x",pady=(2,0))
    def _dis(): settings.set("wayland_banner",False); wf.destroy()
    tk.Button(wf,text="Dismiss",command=_dis,bg=T("bg3"),fg=T("fg2"),
              relief="flat",font=("Helvetica",8),cursor="hand2").pack(anchor="e",pady=(4,0))

# ── quit button ───────────────────────────────────────────────────────────────
Wsep(_inner)
Wb(_inner,f"Quit  [{settings.get('hk_quit').upper()}]",
   emergency_quit,bg="bg",fg="fg3",hover="bg2",pady=5).pack(fill="x")

# ══════════════════════════════════════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════════════════════════════════════
_auto=settings.get("auto_load_preset")
if _auto:
    try:
        state.events=presets.load_inapp(_auto)
        preset_name_var.set(_auto)
    except:
        try:
            for name,path,sz,fmt in presets.list_files():
                if name==_auto:
                    state.events=presets.load_file(path)
                    preset_name_var.set(_auto); break
        except: pass

_refresh_load_list()

if settings.get("mini_mode"):
    full_outer.pack_forget(); root.geometry("320x90"); mini_btn.config(text="⊞")

def _autosave():
    try: _push_settings()
    except: pass
    root.after(8000,_autosave)
root.after(8000,_autosave)
root.mainloop()
