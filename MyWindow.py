

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import ImageTk, Image
import librosa

from WaterfallGenerator import WaterfallGenerator


def is_power_of_two(x: int) -> bool:
    # True for 1,2,4,8,... (and only for those)
    return x > 0 and (x & (x - 1)) == 0


class MyWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("STFT Waterfall Generator")

        self.__samples = None
        self.__samplerate = None

        self.__waterfall = WaterfallGenerator(dynamic_db=80, bandwidth_hz=3000)

        # Zoom state
        self.__pil_img_full = None
        self.__zoom = 1.0
        self.__zoom_min = 0.1
        self.__zoom_max = 20.0
        self.__zoom_step = 1.25
        self.__updating_slider = False

        # Menu
        self.__menubar = tk.Menu(self)

        self.__filemenu = tk.Menu(self.__menubar, tearoff=0)
        self.__filemenu.add_command(label="Load audio file ...", command=self.onLoadAudio)
        self.__filemenu.add_command(label="Save image ...", command=self.onSaveImage)
        
        self.__filemenu.add_command(label="Exit", command=self.destroy)
        self.__menubar.add_cascade(label="File", menu=self.__filemenu)

        self.__viewmenu = tk.Menu(self.__menubar, tearoff=0)
        self.__viewmenu.add_command(label="Fit to window", command=self.fit_to_window)
        self.__viewmenu.add_command(label="100%", command=self.zoom_100)
        self.__menubar.add_cascade(label="View", menu=self.__viewmenu)

        self.config(menu=self.__menubar)


        # ---------- Modern parameter bar (ttk) ----------

        self.__params = ttk.Frame(self)
        # --- Styles for Apply button ---
        style = ttk.Style(self)
        style.configure("Apply.TButton")                 # normal
        style.configure("ApplyDirty.TButton", font=("TkDefaultFont", 9, "bold"))

        self.__params.pack(side="top", fill="x", padx=8, pady=6)

        # Configure grid columns
        for c in range(5):
            self.__params.columnconfigure(c, weight=0)
        self.__params.columnconfigure(4, weight=1)


        def pow2_list(min_pow=8, max_pow=18):
            return [str(2 ** p) for p in range(min_pow, max_pow + 1)]

        self.__pow2_values = pow2_list(8, 18)

        # Variables preloaded from WaterfallGenerator
        self.__var_dynamic_db = tk.DoubleVar(value=float(self.__waterfall.dynamic_db))
        self.__var_n_fft = tk.StringVar(value=str(self.__waterfall.n_fft))
        self.__var_win_length = tk.StringVar(value=str(self.__waterfall.win_length))
        self.__var_hop_length = tk.StringVar(value=str(self.__waterfall.hop_length))

        self.__var_bw_enabled = tk.BooleanVar(value=(self.__waterfall.bandwidth_hz is not None))
        bw_init = 3000.0 if self.__waterfall.bandwidth_hz is None else float(self.__waterfall.bandwidth_hz)
        self.__var_bandwidth = tk.DoubleVar(value=bw_init)

        # Mark Apply as dirty when parameters change
        self.__var_dynamic_db.trace_add("write", lambda *_: self._mark_params_dirty())
        self.__var_n_fft.trace_add("write", lambda *_: self._mark_params_dirty())
        self.__var_win_length.trace_add("write", lambda *_: self._mark_params_dirty())
        self.__var_hop_length.trace_add("write", lambda *_: self._mark_params_dirty())
        self.__var_bandwidth.trace_add("write", lambda *_: self._mark_params_dirty())
        self.__var_bw_enabled.trace_add("write", lambda *_: self._mark_params_dirty())        

        self.__nyquist_var = tk.StringVar(value="Nyquist: —")

        # Layout
        ttk.Label(self.__params, text="dynamic (dB)").grid(row=0, column=0, sticky="w")
        ttk.Label(self.__params, text="n_fft").grid(row=0, column=1, sticky="w")
        ttk.Label(self.__params, text="win_length").grid(row=0, column=2, sticky="w")
        ttk.Label(self.__params, text="hop_length").grid(row=0, column=3, sticky="w")
        ttk.Label(self.__params, text="bandwidth (Hz)").grid(row=0, column=4, sticky="w")

        self.__spin_dynamic = ttk.Spinbox(
            self.__params, from_=1.0, to=400.0, increment=1.0,
            textvariable=self.__var_dynamic_db, width=10
        )
        self.__spin_dynamic.grid(row=1, column=0, sticky="w", padx=(0, 10))

        self.__combo_nfft = ttk.Combobox(
            self.__params, values=self.__pow2_values,
            textvariable=self.__var_n_fft, width=10, state="readonly"
        )
        self.__combo_nfft.grid(row=1, column=1, sticky="w", padx=(0, 10))

        self.__combo_win = ttk.Combobox(
            self.__params, values=self.__pow2_values,
            textvariable=self.__var_win_length, width=10, state="readonly"
        )
        self.__combo_win.grid(row=1, column=2, sticky="w", padx=(0, 10))

        self.__combo_hop = ttk.Combobox(
            self.__params, values=self.__pow2_values,
            textvariable=self.__var_hop_length, width=10, state="readonly"
        )
        self.__combo_hop.grid(row=1, column=3, sticky="w", padx=(0, 10))

        bw_row = ttk.Frame(self.__params)
        bw_row.grid(row=1, column=4, sticky="we", padx=(0, 10))


        self.__chk_bw = ttk.Checkbutton(
            bw_row, text="limit",
            variable=self.__var_bw_enabled,
            command=self._on_bw_toggle
        )
        self.__chk_bw.pack(side="left")

        self.__spin_bw = ttk.Spinbox(
            bw_row, from_=0.0, to=1_000_000.0,
            increment=100.0, textvariable=self.__var_bandwidth, width=10
        )
        self.__spin_bw.pack(side="left", padx=(8, 8))

        ttk.Label(bw_row, textvariable=self.__nyquist_var).pack(side="left")

        self.__btn_apply = ttk.Button(
            bw_row,
            text="Apply",
            command=self._apply_params,
            style="Apply.TButton",
        )
        self.__btn_apply.pack(side="left", padx=(10, 0))


        self.__combo_nfft.bind("<<ComboboxSelected>>", self._on_nfft_changed)
        self.__combo_win.bind("<<ComboboxSelected>>", self._on_win_changed)

        self._on_bw_toggle()


       
        # ---------- Canvas + scrollbars ----------
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        self.__canvas = tk.Canvas(container, highlightthickness=0)
        self.__hbar = tk.Scrollbar(container, orient="horizontal", command=self.__canvas.xview)
        self.__vbar = tk.Scrollbar(container, orient="vertical", command=self.__canvas.yview)
        self.__canvas.configure(xscrollcommand=self.__hbar.set, yscrollcommand=self.__vbar.set)

        self.__hbar.pack(side="bottom", fill="x")
        self.__vbar.pack(side="right", fill="y")
        self.__canvas.pack(side="left", fill="both", expand=True)

        self.__tk_img = None
        self.__canvas_img_id = None

        # ---------- Status bar ----------
        status = tk.Frame(self, bd=1, relief="sunken")
        status.pack(side="bottom", fill="x")

        self.__status_var = tk.StringVar(value="No image loaded")
        tk.Label(status, textvariable=self.__status_var, anchor="w").pack(
            side="left", fill="x", expand=True, padx=(6, 8), pady=2
        )

        controls = tk.Frame(status)
        controls.pack(side="right", padx=6, pady=1)

        btn_kw = dict(takefocus=0, padx=6, pady=0)

        self.__btn_minus = tk.Button(controls, text="–", width=2, command=self.zoom_out, **btn_kw)
        self.__btn_minus.pack(side="left")

        self.__zoom_var = tk.IntVar(value=100)
        self.__zoom_slider = tk.Scale(
            controls,
            from_=int(self.__zoom_min * 100),
            to=int(self.__zoom_max * 100),
            orient="horizontal",
            showvalue=False,
            variable=self.__zoom_var,
            command=self._on_zoom_slider,
            length=120,
            sliderlength=14,
            takefocus=0,
            bd=0,
            highlightthickness=0,
        )
        self.__zoom_slider.pack(side="left", padx=4)

        self.__btn_plus = tk.Button(controls, text="+", width=2, command=self.zoom_in, **btn_kw)
        self.__btn_plus.pack(side="left")

        # Fixed slot for the zoom percentage so an Entry can appear in-place
        self.__zoom_pct_slot = tk.Frame(controls)
        self.__zoom_pct_slot.pack(side="left", padx=(4, 8))

        self.__zoom_pct_var = tk.StringVar(value="100%")
        self.__zoom_pct_label = tk.Label(self.__zoom_pct_slot, textvariable=self.__zoom_pct_var, width=6, anchor="e")
        self.__zoom_pct_label.pack(side="left")
        self.__zoom_pct_label.bind("<Button-1>", self._start_zoom_edit)

        tk.Label(controls, text="|", padx=6).pack(side="left")

        self.__btn_fit = tk.Button(controls, text="Fit", command=self.fit_to_window, **btn_kw)
        self.__btn_fit.pack(side="left")

        self.__btn_100 = tk.Button(controls, text="100%", command=self.zoom_100, **btn_kw)
        self.__btn_100.pack(side="left", padx=(4, 0))

        self.__btn_125 = tk.Button(controls, text="125%", command=lambda: self._set_zoom(1.25, None), **btn_kw)
        self.__btn_125.pack(side="left", padx=(4, 0))

        # Zoom bindings
        self.__canvas.bind("<Control-MouseWheel>", self._on_ctrl_mousewheel)
        self.__canvas.bind("<Control-Button-4>", self._on_ctrl_wheel_linux)
        self.__canvas.bind("<Control-Button-5>", self._on_ctrl_wheel_linux)

        self._set_zoom_controls_enabled(False)

    # ---------- Parameter handling ----------

    def _apply_params(self):
        # Read and validate parameters from the UI, then update WaterfallGenerator
        try:
            dynamic_db = float(self.__var_dynamic_db.get())
            n_fft = int(self.__var_n_fft.get())
            win_length = int(self.__var_win_length.get())
            hop_length = int(self.__var_hop_length.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter numeric values for dynamic_db, n_fft, win_length, hop_length.")
            return

        # bandwidth: only relevant if enabled
        bw_enabled = self.__var_bw_enabled.get()
        bandwidth_hz = None
        if bw_enabled:
            try:
                bandwidth_hz = float(self.__var_bandwidth.get())
            except ValueError:
                messagebox.showerror("Invalid input", "Please enter a numeric value for bandwidth.")
                return

        # Validation rules
        if dynamic_db <= 0:
            messagebox.showerror("Invalid dynamic_db", "dynamic_db must be > 0.")
            return

        for name, val in (("n_fft", n_fft), ("win_length", win_length), ("hop_length", hop_length)):
            if not is_power_of_two(val):
                messagebox.showerror("Invalid value", f"{name} must be a power of two.")
                return

        if win_length > n_fft:
            messagebox.showerror("Invalid relation", "win_length must be <= n_fft.")
            return

        if bandwidth_hz is not None:
            if bandwidth_hz < 0:
                messagebox.showerror("Invalid bandwidth", "bandwidth must be >= 0.")
                return
            if self.__samplerate is not None:
                nyquist = float(self.__samplerate) / 2.0
                if bandwidth_hz > nyquist:
                    messagebox.showerror("Invalid bandwidth", f"bandwidth must be <= Nyquist ({nyquist:.0f} Hz).")
                    return

        # Apply to generator (these names match your waterfall.py)
        self.__waterfall.dynamic_db = dynamic_db
        self.__waterfall.n_fft = n_fft
        self.__waterfall.win_length = win_length
        self.__waterfall.hop_length = hop_length
        self.__waterfall.bandwidth_hz = bandwidth_hz

        # If audio is loaded, re-render the waterfall
        if self.__samples is not None and self.__samplerate is not None:
            self._render_waterfall_full()
            self.fit_to_window()

        self._clear_params_dirty()

    # ---------- UI helpers ----------

    def _set_zoom_controls_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for w in (
            self.__btn_minus, self.__btn_plus,
            self.__btn_fit, self.__btn_100, self.__btn_125,
            self.__zoom_slider,
        ):
            w.configure(state=state)

    def _set_slider_from_zoom(self):
        self.__updating_slider = True
        try:
            pct = int(round(self.__zoom * 100))
            self.__zoom_var.set(pct)
            self.__zoom_pct_var.set(f"{pct}%")
        finally:
            self.__updating_slider = False

    def _update_status(self, full_w: int, full_h: int, shown_w: int, shown_h: int):
        self.__status_var.set(f"image {full_w}×{full_h} px   shown {shown_w}×{shown_h} px")

    # ---------- Load + render ----------

    def onLoadAudio(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Audio files", "*.wav *.flac *.ogg *.mp3 *.aiff *.aif *.m4a"),
                ("All files", "*.*"),
            ]
        )
        if not file_path:
            return

        try:
            self.__samples, self.__samplerate = librosa.load(file_path, sr=None)
            self.__nyquist_var.set(f"Nyquist: {int(self.__samplerate / 2)} Hz")


            # If bandwidth limiting is enabled, ensure it's not above Nyquist and reflect it in the UI
            if self.__var_bw_enabled.get():
                try:
                    bw = float(self.__var_bandwidth.get())
                except ValueError:
                    bw = 0.0

                nyquist = float(self.__samplerate) / 2.0
                if bw > nyquist:
                    bw = nyquist
                    self.__var_bandwidth.set(str(int(nyquist)))

            self._render_waterfall_full()
            self.fit_to_window()
            self._set_zoom_controls_enabled(True)
        except Exception as e:
            print(e)

    def onSaveImage(self):
        """Save the currently rendered waterfall image to disk."""
        if self.__pil_img_full is None:
            messagebox.showinfo("Save image", "No image to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG image", "*.png"),
                ("JPEG image", "*.jpg *.jpeg"),
                ("TIFF image", "*.tif *.tiff"),
                ("BMP image", "*.bmp"),
            ],
            title="Save image",
        )
        if not file_path:
            return

        try:
            # Use format inferred from extension; ensure RGB for formats that do not support arbitrary modes well.
            img = self.__pil_img_full
            ext = file_path.lower().rsplit(".", 1)[-1] if "." in file_path else ""

            # JPEG doesn't support alpha; we are RGB anyway, but keep it explicit.
            if ext in ("jpg", "jpeg"):
                img = img.convert("RGB")

            img.save(file_path)
        except Exception as e:
            messagebox.showerror("Save image failed", str(e))


    def _render_waterfall_full(self):
        if self.__samples is None or self.__samplerate is None:
            return

        self.__pil_img_full = self.__waterfall.build_image(self.__samples, int(self.__samplerate))
        self.__zoom = 1.0
        self._set_slider_from_zoom()
        self._redraw_at_current_zoom(anchor_canvas_xy=None)

    # ---------- Zoom / redraw ----------

    def _redraw_at_current_zoom(self, anchor_canvas_xy):
        if self.__pil_img_full is None:
            return

        # Keep the anchor point stable while zooming (relative to the current scroll region)
        if anchor_canvas_xy is not None:
            ax, ay = anchor_canvas_xy
            sr = self.__canvas.cget("scrollregion")
            if sr:
                x0, y0, x1, y1 = map(float, sr.split())
                old_w = max(1.0, x1 - x0)
                old_h = max(1.0, y1 - y0)
                rel_x = (self.__canvas.canvasx(ax) - x0) / old_w
                rel_y = (self.__canvas.canvasy(ay) - y0) / old_h
            else:
                rel_x = rel_y = None
        else:
            rel_x = rel_y = None

        full_w, full_h = self.__pil_img_full.size
        new_w = max(1, int(full_w * self.__zoom))
        new_h = max(1, int(full_h * self.__zoom))

        # Pixel-accurate zoom (no interpolation)
        pil_zoomed = self.__pil_img_full.resize((new_w, new_h), resample=Image.Resampling.NEAREST)
        self.__tk_img = ImageTk.PhotoImage(pil_zoomed)

        if self.__canvas_img_id is None:
            self.__canvas_img_id = self.__canvas.create_image(0, 0, anchor="nw", image=self.__tk_img)
        else:
            self.__canvas.itemconfigure(self.__canvas_img_id, image=self.__tk_img)

        self.__canvas.configure(scrollregion=(0, 0, new_w, new_h))

        if rel_x is not None and rel_y is not None:
            self.__canvas.xview_moveto(rel_x)
            self.__canvas.yview_moveto(rel_y)
        else:
            self.__canvas.xview_moveto(0.0)
            self.__canvas.yview_moveto(0.0)

        self._update_status(full_w, full_h, new_w, new_h)
        self._set_slider_from_zoom()

    def _set_zoom(self, new_zoom, anchor_event):
        if self.__pil_img_full is None:
            return

        new_zoom = max(self.__zoom_min, min(self.__zoom_max, float(new_zoom)))
        if abs(new_zoom - self.__zoom) < 1e-9:
            return

        self.__zoom = new_zoom
        anchor_xy = (anchor_event.x, anchor_event.y) if anchor_event is not None else None
        self._redraw_at_current_zoom(anchor_canvas_xy=anchor_xy)

    def zoom_in(self, anchor_event=None):
        self._set_zoom(self.__zoom * self.__zoom_step, anchor_event)

    def zoom_out(self, anchor_event=None):
        self._set_zoom(self.__zoom / self.__zoom_step, anchor_event)

    def zoom_100(self):
        self._set_zoom(1.0, anchor_event=None)

    def fit_to_window(self):
        if self.__pil_img_full is None:
            return

        self.update_idletasks()
        cw = max(1, self.__canvas.winfo_width())
        ch = max(1, self.__canvas.winfo_height())

        iw, ih = self.__pil_img_full.size
        z = min(cw / iw, ch / ih)
        z = max(self.__zoom_min, min(self.__zoom_max, z))

        self._set_zoom(z, anchor_event=None)

    # ---------- Slider callback ----------

    def _on_zoom_slider(self, _value_as_str):
        if self.__updating_slider or self.__pil_img_full is None:
            return
        pct = self.__zoom_var.get()
        self.__zoom_pct_var.set(f"{pct}%")
        self._set_zoom(pct / 100.0, anchor_event=None)

    # ---------- Event handlers ----------

    def _on_ctrl_mousewheel(self, event):
        if self.__pil_img_full is None:
            return
        if event.delta > 0:
            self._set_zoom(self.__zoom * self.__zoom_step, anchor_event=event)
        else:
            self._set_zoom(self.__zoom / self.__zoom_step, anchor_event=event)

    def _on_ctrl_wheel_linux(self, event):
        if self.__pil_img_full is None:
            return
        if event.num == 4:
            self._set_zoom(self.__zoom * self.__zoom_step, anchor_event=event)
        elif event.num == 5:
            self._set_zoom(self.__zoom / self.__zoom_step, anchor_event=event)

    # ---------- Inline zoom edit (fixed slot) ----------

    def _start_zoom_edit(self, event=None):
        if self.__pil_img_full is None:
            return

        for w in self.__zoom_pct_slot.winfo_children():
            w.destroy()

        self.__zoom_entry = tk.Entry(self.__zoom_pct_slot, width=5, justify="right")
        self.__zoom_entry.insert(0, str(int(round(self.__zoom * 100))))
        self.__zoom_entry.pack(side="left")

        self.__zoom_entry.focus_set()
        self.__zoom_entry.select_range(0, "end")

        self.__zoom_entry.bind("<Return>", self._finish_zoom_edit)
        self.__zoom_entry.bind("<Escape>", self._cancel_zoom_edit)
        self.__zoom_entry.bind("<FocusOut>", self._cancel_zoom_edit)

    def _finish_zoom_edit(self, event=None):
        try:
            value = int(self.__zoom_entry.get())
            self._set_zoom(value / 100.0, anchor_event=None)
        except ValueError:
            pass
        self._end_zoom_edit()

    def _cancel_zoom_edit(self, event=None):
        self._end_zoom_edit()

    def _end_zoom_edit(self):
        for w in self.__zoom_pct_slot.winfo_children():
            w.destroy()

        self.__zoom_pct_label = tk.Label(self.__zoom_pct_slot, textvariable=self.__zoom_pct_var, width=6, anchor="e")
        self.__zoom_pct_label.pack(side="left")
        self.__zoom_pct_label.bind("<Button-1>", self._start_zoom_edit)

        self._set_slider_from_zoom()

    def _on_bw_toggle(self):
        """Enable or disable the bandwidth spinbox."""
        state = "normal" if self.__var_bw_enabled.get() else "disabled"
        self.__spin_bw.configure(state=state)

    def _on_nfft_changed(self, event=None):
        """Ensure win_length <= n_fft."""
        try:
            n_fft = int(self.__var_n_fft.get())
            win = int(self.__var_win_length.get())
        except ValueError:
            return

        if win > n_fft:
            self.__var_win_length.set(str(n_fft))

    def _on_win_changed(self, event=None):
        """Keep win_length <= n_fft constraint."""
        self._on_nfft_changed()

    def _mark_params_dirty(self):
        """Highlight Apply button to indicate pending parameter changes."""
        self.__btn_apply.configure(style="ApplyDirty.TButton")

    def _clear_params_dirty(self):
        """Reset Apply button appearance after applying parameters."""
        self.__btn_apply.configure(style="Apply.TButton")


if __name__ == "__main__":
    MyWindow().mainloop()
