"""Run this file in VS Code. Camera starts only after the explicit start button."""
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
try:
    import tkinter as tk
except ModuleNotFoundError:
    # This machine's 3.12 lacks Tcl/Tk; use installed 3.14 only for the GUI.
    # The inference worker still uses the project's isolated 3.12 environment.
    if __name__ == "__main__":
        raise SystemExit(subprocess.call(["py", "-3.14", str(Path(__file__).resolve())]))
    raise
from tkinter import ttk, filedialog, messagebox

ROOT=Path(__file__).resolve().parent
ENGINE=ROOT/".venv/Scripts/python.exe"


class App:
    def __init__(self,root):
        self.root=root
        self.process=None
        self.messages=queue.Queue()
        self.latest=None
        root.title("康复训练视觉演示 v0.7 · 动作1量化标准")
        root.geometry("900x850")
        root.minsize(800,840)
        frame=ttk.Frame(root,padding=24)
        frame.pack(fill="both",expand=True)
        ttk.Label(frame,text="康复动作 · 视觉测量演示",font=("Microsoft YaHei UI",20,"bold")).pack(anchor="w")
        ttk.Label(frame,text="动作1继续优化｜动作2、6、8为实验规则｜测试参数不作为临床处方").pack(anchor="w",pady=(8,12))
        ttk.Label(frame,text="在下面选择训练侧后直接开始，无需按键确认腿。\n放下小腿坐稳约2秒，等标定完成；B重新标定，跟错腿时L/K切换模型侧。",
                  justify="left").pack(anchor="w",pady=(0,16))
        options=ttk.Frame(frame)
        options.pack(fill="x")
        ttk.Label(options,text="训练侧：").grid(row=0,column=0)
        self.side=tk.StringVar(value="左腿")
        ttk.Combobox(options,textvariable=self.side,values=["左腿","右腿"],state="readonly",width=8).grid(row=0,column=1,padx=8)
        ttk.Label(options,text="摄像头编号：").grid(row=0,column=2)
        self.camera=tk.StringVar(value="0")
        ttk.Combobox(options,textvariable=self.camera,values=["0","1","2","3"],state="readonly",width=5).grid(row=0,column=3)
        ttk.Label(options,text='画质：').grid(row=0,column=4,padx=(12,4))
        self.resolution=tk.StringVar(value='720p')
        ttk.Combobox(options,textvariable=self.resolution,values=['480p','720p','1080p'],state='readonly',width=8).grid(row=0,column=5)
        ttk.Label(options,text="识别模型：").grid(row=1,column=0,pady=(14,0))
        self.backend=tk.StringVar(value="RTMPose（新增对比方案）")
        ttk.Combobox(options,textvariable=self.backend,values=["RTMPose（新增对比方案）","MediaPipe（原方案）"],state="readonly",width=26).grid(row=1,column=1,columnspan=3,sticky="w",pady=(14,0))
        ttk.Label(options,text="RTMPose取景：").grid(row=2,column=0,pady=(10,0))
        self.roi=tk.StringVar(value="固定单人画面（近景）")
        ttk.Combobox(options,textvariable=self.roi,values=["固定单人画面（近景）","先检测人体（全景）","锁定训练者（需确认）"],state="readonly",width=26).grid(row=2,column=1,columnspan=3,sticky="w",pady=(10,0))
        ttk.Label(options,text='训练动作：').grid(row=3,column=0,pady=(10,0))
        self.exercise=tk.StringVar(value='1 坐姿伸膝')
        ttk.Combobox(options,textvariable=self.exercise,values=['1 坐姿伸膝','2 卧姿直腿抬高（实验）','6 扶物微蹲（实验）','8 坐站（实验）'],state='readonly',width=26).grid(row=3,column=1,columnspan=3,sticky='w',pady=(10,0))
        ttk.Label(options,text='脚伸出方向：').grid(row=4,column=0,pady=(10,0))
        self.facing=tk.StringVar(value='画面左侧')
        ttk.Combobox(options,textvariable=self.facing,values=['画面左侧','画面右侧'],state='readonly',width=26).grid(row=4,column=1,columnspan=3,sticky='w',pady=(10,0))
        planbox=ttk.LabelFrame(frame,text='本次训练计划（动作2/6/8为实验规则，非临床处方）',padding=6)
        planbox.pack(fill='x',pady=(10,0))
        self.plan_sets=tk.StringVar(value='3');self.plan_reps=tk.StringVar(value='10');self.plan_hold=tk.StringVar(value='3')
        for column,(label,var,values) in enumerate([('组数',self.plan_sets,['3','4','5']),('每组次数',self.plan_reps,['10','11','12','13','14','15']),('保持秒数',self.plan_hold,['3','2','2.5','5'])]):
            ttk.Label(planbox,text=label).grid(row=0,column=column*2,padx=4)
            if var is self.plan_reps:
                self.reps_entry=ttk.Entry(planbox,textvariable=var,width=7)
                self.reps_entry.grid(row=0,column=column*2+1,padx=4)
            else:
                selector=ttk.Combobox(planbox,textvariable=var,values=values,state='readonly',width=5)
                selector.grid(row=0,column=column*2+1,padx=4)
                if var is self.plan_hold:self.hold_selector=selector
        self.exercise.trace_add('write',self.exercise_changed)
        ttk.Label(planbox,text='组间休息30秒；次数统计完整动作，不等于全部达标。').grid(row=1,column=0,columnspan=6,sticky='w',pady=(5,0))
        self.save=tk.BooleanVar(value=False)
        ttk.Checkbutton(frame,text="保存原画面和标注视频到本机（默认关闭，会保存两份录像）",variable=self.save).pack(anchor="w",pady=12)
        ttk.Label(frame,text="锁定模式：点击人体框后按 C 确认；仅一人时直接按 C；按 R 重选。\n近景模式不防旁人干扰。初始姿势：1/8坐好，2平躺直腿，6扶稳站立。",
                  justify="left").pack(anchor="w",pady=(0,12))
        buttons=ttk.Frame(frame)
        buttons.pack(fill="x")
        self.start=ttk.Button(buttons,text="允许使用摄像头并开始",command=self.start_camera)
        self.start.pack(side="left",padx=(0,8))
        self.video=ttk.Button(buttons,text="选择本地视频",command=self.start_video)
        self.video.pack(side="left",padx=(0,8))
        self.stop=ttk.Button(buttons,text="停止",command=self.stop_run,state="disabled")
        self.stop.pack(side="left")
        self.pause=ttk.Button(buttons,text='暂停 / 恢复',command=self.toggle_pause,state='disabled')
        self.pause.pack(side='left',padx=8)
        self.status=tk.StringVar(value="准备就绪。首次运行会检查依赖和模型。")
        ttk.Label(frame,textvariable=self.status,wraplength=700).pack(anchor="w",pady=14)
        self.log=tk.Text(frame,height=6,wrap="word",state="disabled",font=("Microsoft YaHei UI",10))
        self.log.pack(fill="both",expand=True)
        ttk.Button(frame,text="打开最近一次结果文件夹",command=self.open_result).pack(anchor="w",pady=(12,0))
        ttk.Label(frame,text="画面中的角度为二维估计值；不能测量肌肉发力或诊断病情。\n橙色虚线表示短暂预测，不计算保持时间；持续丢点会中断本次动作。").pack(anchor="w",pady=(10,0))
        root.protocol("WM_DELETE_WINDOW",self.close)
        root.after(100,self.poll)
        self.busy=False

    def append(self,text):
        self.log.configure(state="normal")
        self.log.insert("end",text+"\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def start_camera(self):
        self.launch(["--camera",self.camera.get()])

    def exercise_changed(self,*args):
        values={'1':['3','2','2.5','5'],'2':['5'],'6':['0'],'8':['0']}[self.exercise.get()[0]]
        self.hold_selector.configure(values=values)
        self.plan_hold.set(values[0])

    def start_video(self):
        path=filedialog.askopenfilename(title="选择侧面拍摄的动作视频",filetypes=[("视频","*.mp4 *.mov *.avi *.mkv"),("所有文件","*.*")])
        if path:
            self.launch(["--video",path])

    def launch(self,source):
        if self.busy:
            return
        if self.exercise.get()[0] in ('1','2','6','8'):
            value=self.plan_reps.get().strip()
            if not value.isascii() or not value.isdecimal() or not 1<=int(value)<=100:
                messagebox.showerror('次数填写有误','每组次数请输入1～100之间的整数，例如8或12。此范围是软件输入限制，不是训练建议。')
                self.reps_entry.focus_set()
                return
            self.plan_reps.set(str(int(value)))
        if not ENGINE.exists():
            messagebox.showerror("需要安装依赖","请先运行 setup.ps1，创建本项目的 .venv 环境。")
            return
        self.latest=ROOT/"results"/datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backend="rtmpose" if self.backend.get().startswith("RTM") else "mediapipe"
        if self.roi.get().startswith('锁定') and backend!='rtmpose':
            messagebox.showinfo('模型选择','锁定训练者模式目前需要选择RTMPose。');return
        args=[str(ENGINE),"-u","-m","rehab_pose.run",*source,"--side",
              "left" if self.side.get()=="左腿" else "right","--backend",backend,"--preview","--output",str(self.latest)]
        roi='full-frame' if self.roi.get().startswith('固定') else 'locked' if self.roi.get().startswith('锁定') else 'detected'
        args.extend(['--rtm-roi',roi,'--facing','left' if self.facing.get()=='画面左侧' else 'right','--exercise',self.exercise.get()[0]])
        args.extend(['--camera-resolution',self.resolution.get()])
        self.active_plan=True
        if self.active_plan:
            args.extend(['--sets',self.plan_sets.get(),'--reps-per-set',self.plan_reps.get(),'--hold-seconds',self.plan_hold.get()])
            self.append(f'本次单侧计划：{self.plan_sets.get()}组×{self.plan_reps.get()}次，保持{self.plan_hold.get()}秒，组间休息30秒。')
        if not self.save.get():
            args.append("--no-save-video")
        self.busy=True
        self.reps_entry.configure(state='disabled')
        self.start.configure(state="disabled")
        self.video.configure(state="disabled")
        self.status.set("正在准备模型，随后打开视频窗口……")
        self.append("准备启动。停止可点击本窗口按钮，或在视频窗口按 Q / Esc。")
        def worker():
            try:
                from rehab_pose.model import download_model,download_rtmpose
                if backend=="rtmpose":
                    download_rtmpose(ROOT/"models/rtmpose",roi)
                else:
                    download_model(ROOT/"models/pose_landmarker_full.task")
                # A stop-file permits clean finalization and flushing of the result files.
                self.process=subprocess.Popen(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                              text=True,encoding="utf-8",errors="replace",creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                self.messages.put(("started",None))
                for line in self.process.stdout:
                    self.messages.put(("log",line.rstrip()))
                code=self.process.wait()
                self.messages.put(("done",code))
            except Exception as exc:
                self.messages.put(("log",str(exc)))
                self.messages.put(("done",1))
        threading.Thread(target=worker,daemon=True).start()

    def stop_run(self):
        if self.latest and self.latest.exists():
            (self.latest/"STOP").touch()
            self.status.set("正在停止并保存结果……")

    def toggle_pause(self):
        if self.latest and self.latest.exists() and self.process:
            (self.latest/'PAUSE_TOGGLE').touch()
            self.append('已请求暂停/恢复，当前状态请看视频窗口。')

    def poll(self):
        while not self.messages.empty():
            kind,value=self.messages.get()
            if kind=="log":
                self.append(value)
            elif kind=="started":
                self.stop.configure(state="normal")
                self.pause.configure(state='normal' if self.active_plan else 'disabled')
                self.status.set("正在分析。若没有画面，请查看下面日志。")
            elif kind=="done":
                self.busy=False
                self.reps_entry.configure(state='normal')
                self.process=None
                self.start.configure(state="normal")
                self.video.configure(state="normal")
                self.stop.configure(state="disabled")
                self.pause.configure(state='disabled')
                self.status.set("分析结束，结果已保存在本机。" if value==0 else "运行失败，请查看日志；检查摄像头权限、编号及模型下载。")
                summary=self.latest/"summary.json"
                if summary.exists():
                    data=json.loads(summary.read_text(encoding="utf-8"))
                    self.append(f"完整动作次数：{data['completed_reps']}；可靠帧：{data['reliable_frames']}/{data['frames']}")
                    if data.get('exercise')=='SEATED_KNEE_EXTENSION':
                        self.append(f"达到目标角度并保持达标：{data.get('target_completed_reps',0)}次")
                    self.append(str(self.latest))
        self.root.after(100,self.poll)

    def open_result(self):
        import os
        if self.latest and self.latest.exists():
            os.startfile(self.latest)
        else:
            messagebox.showinfo("结果","请先完成一次分析。")

    def close(self):
        if self.busy:
            self.stop_run()
            self.status.set("请等待本次运行结束，再关闭窗口。")
            return
        self.root.destroy()


if __name__=="__main__":
    root=tk.Tk()
    App(root)
    root.mainloop()
