import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib
import time
import math
import random
import os
from datetime import datetime

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    from mpl_toolkits.mplot3d import Axes3D
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ==================== THEME & STYLING ====================
BG = "#0B0E14"
CARD = "#161A24"
ACCENT = "#6B4EFF"
ACCENT2 = "#22E0B8"
TEXT = "#EEF1F8"
MUTED = "#8891A8"
DANGER = "#FF5D6C"
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_H1 = ("Segoe UI", 22, "bold")
FONT_STAT = ("Segoe UI", 24, "bold")


def make_button(parent, **options):
    background = options.get("bg", CARD)
    foreground = options.get("fg", TEXT)
    return tk.Button(
        parent,
        activebackground=background,
        activeforeground=foreground,
        disabledforeground=foreground,
        **options,
    )


# ==================== DATABASE LAYER ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("aurum_tracker.db")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                pin_hash TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                description TEXT
            )
        """)
        self.conn.commit()

    def hash_text(self, text):
        return hashlib.sha256(text.encode()).hexdigest()

    def user_exists(self, username):
        self.cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        return self.cursor.fetchone() is not None

    def register_user(self, username, password):
        try:
            self.cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                                (username, self.hash_text(password)))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def setup_pin(self, username, pin):
        self.cursor.execute("UPDATE users SET pin_hash=? WHERE username=?", 
                            (self.hash_text(pin), username))
        self.conn.commit()

    def verify_login(self, username, password, pin):
        self.cursor.execute("SELECT password_hash, pin_hash FROM users WHERE username=?", (username,))
        row = self.cursor.fetchone()
        if row:
            return row["password_hash"] == self.hash_text(password) and row["pin_hash"] == self.hash_text(pin)
        return False

    def verify_pin(self, username, pin):
        self.cursor.execute("SELECT pin_hash FROM users WHERE username=?", (username,))
        row = self.cursor.fetchone()
        if row and row["pin_hash"]:
            return row["pin_hash"] == self.hash_text(pin)
        return False

    def add_transaction(self, username, t_type, category, amount, description):
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cursor.execute("INSERT INTO transactions (username, type, category, amount, date, description) VALUES (?,?,?,?,?,?)",
                            (username, t_type, category, amount, date, description))
        self.conn.commit()

    def get_transactions(self, username):
        self.cursor.execute("SELECT * FROM transactions WHERE username=? ORDER BY date DESC", (username,))
        return self.cursor.fetchall()

    def delete_transaction(self, t_id):
        self.cursor.execute("DELETE FROM transactions WHERE id=?", (t_id,))
        self.conn.commit()

    def get_summary(self, username):
        self.cursor.execute("SELECT type, SUM(amount) as total FROM transactions WHERE username=? GROUP BY type", (username,))
        rows = self.cursor.fetchall()
        income = sum(r["total"] for r in rows if r["type"] == "Income")
        expense = sum(r["total"] for r in rows if r["type"] == "Expense")
        return income, expense, (income - expense)

db = Database()

# ==================== ANIMATED PET CAT ====================
class AnimatedPet(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, bg=CARD, highlightthickness=0, width=120, height=100)
        self.bind("<Configure>", self._draw)
        self.tail_angle = 0
        self.bob_y = 0
        self.target_bob = 0
        self.animate()

    def _draw(self, event=None):
        self.delete("all")
        cx, cy = self.winfo_width()//2, self.winfo_height()//2 + self.bob_y
        
        # Shadow
        self.create_oval(cx-30, cy+25, cx+30, cy+35, fill="#0B0E14", outline="")
        
        # Tail
        tail_x = cx + 25 + math.sin(self.tail_angle) * 10
        tail_y = cy + 10 + math.cos(self.tail_angle) * 5
        self.create_line(cx+15, cy+15, tail_x, tail_y, width=6, fill=ACCENT, smooth=True, capstyle="round")
        
        # Body
        self.create_oval(cx-20, cy-10, cx+25, cy+30, fill=ACCENT, outline="")
        
        # Head
        self.create_oval(cx-35, cy-30, cx+5, cy+10, fill=ACCENT, outline="")
        
        # Ears
        self.create_polygon(cx-30, cy-25, cx-20, cy-45, cx-10, cy-25, fill=ACCENT, outline="")
        self.create_polygon(cx-15, cy-25, cx-5, cy-45, cx+5, cy-25, fill=ACCENT, outline="")
        
        # Eyes
        self.create_oval(cx-28, cy-20, cx-22, cy-14, fill=BG, outline="")
        self.create_oval(cx-12, cy-20, cx-6, cy-14, fill=BG, outline="")
        
        # Nose
        self.create_polygon(cx-19, cy-8, cx-15, cy-8, cx-17, cy-4, fill=DANGER, outline="")

    def animate(self):
        self.tail_angle += 0.2
        if random.random() < 0.05:
            self.target_bob = random.choice([-10, 10, 0])
        self.bob_y += (self.target_bob - self.bob_y) * 0.1
        
        try:
            self._draw()
            self.after(50, self.animate)
        except tk.TclError:
            pass

# ==================== APP ROOT & TRANSITIONS ====================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Safewheel - Smart Expense Tracker")
        self.geometry("1000x700")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self.current_user = None
        self.current_frame = None
        
        # Ttk Styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT, rowheight=35, borderwidth=0, font=FONT)
        style.configure("Treeview.Heading", background="#1C2234", foreground=MUTED, font=FONT_BOLD, relief="flat")
        style.map("Treeview", background=[("selected", ACCENT)])
        
        self.show_frame(SplashScreen)

    def show_frame(self, frame_class, *args, **kwargs):
        if self.current_frame:
            try:
                self.current_frame.destroy()
            except Exception:
                pass
            
        # Fade out transition
        self.attributes('-alpha', 1.0)
        for i in range(10):
            self.attributes('-alpha', 1.0 - i/10)
            self.update()
            time.sleep(0.01)
            
        self.current_frame = frame_class(self, *args, **kwargs)
        self.current_frame.pack(fill="both", expand=True)
        
        # Fade in transition
        for i in range(10):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.01)

# ==================== SCREENS ====================
class SplashScreen(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG)
        self.c = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.c.create_text(500, 300, text="SAFEWHEEL", fill=ACCENT, font=("Segoe UI", 40, "bold"))
        self.c.create_text(500, 350, text="Smart Expense Tracker", fill=MUTED, font=("Segoe UI", 14))
        self.after(1500, lambda: self.master.show_frame(AuthScreen))

class AuthScreen(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG)
        self.mode = "login"
        self._build()
        self._render_form()

    def _build(self):
        self.card = tk.Frame(self, bg=CARD, padx=40, pady=40)
        self.card.place(relx=0.5, rely=0.5, anchor="center", width=400)
        
        tk.Label(self.card, text="SAFEWHEEL", bg=CARD, fg=ACCENT, font=("Segoe UI", 20, "bold")).pack(pady=(0, 10))
        
        self.seg_frame = tk.Frame(self.card, bg="#0B0E14")
        self.seg_frame.pack(fill="x", pady=10)
        
        self.btn_login = make_button(self.seg_frame, text="Login", bg=ACCENT, fg=TEXT, relief="flat", command=lambda: self._switch("login"))
        self.btn_login.pack(side="left", fill="x", expand=True, ipady=5)
        
        self.btn_reg = make_button(self.seg_frame, text="Register", bg=CARD, fg=MUTED, relief="flat", command=lambda: self._switch("register"))
        self.btn_reg.pack(side="left", fill="x", expand=True, ipady=5)

        self.form = tk.Frame(self.card, bg=CARD)
        self.form.pack(fill="x", pady=10)
        
        self.err_lbl = tk.Label(self.card, text="", fg=DANGER, bg=CARD, font=("Segoe UI", 9))
        self.err_lbl.pack()

    def _switch(self, mode):
        self.mode = mode
        if mode == "login":
            self.btn_login.configure(bg=ACCENT, fg=TEXT, activebackground=ACCENT, activeforeground=TEXT)
            self.btn_reg.configure(bg=CARD, fg=MUTED, activebackground=CARD, activeforeground=MUTED)
        else:
            self.btn_reg.configure(bg=ACCENT, fg=TEXT, activebackground=ACCENT, activeforeground=TEXT)
            self.btn_login.configure(bg=CARD, fg=MUTED, activebackground=CARD, activeforeground=MUTED)
        self._render_form()

    def _render_form(self):
        for w in self.form.winfo_children():
            w.destroy()
        self.err_lbl.config(text="")
        
        if self.mode == "login":
            tk.Label(self.form, text="Username", bg=CARD, fg=MUTED).pack(anchor="w")
            self.e_user = tk.Entry(self.form, bg="#1C2234", fg=TEXT, insertbackground=TEXT, relief="flat")
            self.e_user.pack(fill="x", ipady=5, pady=(0, 10))
            
            tk.Label(self.form, text="Password", bg=CARD, fg=MUTED).pack(anchor="w")
            self.e_pass = tk.Entry(self.form, bg="#1C2234", fg=TEXT, insertbackground=TEXT, relief="flat", show="*")
            self.e_pass.pack(fill="x", ipady=5, pady=(0, 10))

            tk.Label(self.form, text="Security PIN (4 digits)", bg=CARD, fg=MUTED).pack(anchor="w")
            self.e_pin = tk.Entry(self.form, bg="#1C2234", fg=TEXT, insertbackground=TEXT, relief="flat", show="*")
            self.e_pin.pack(fill="x", ipady=5, pady=(0, 20))
            
            make_button(self.form, text="Unlock", bg=ACCENT, fg=TEXT, relief="flat", font=FONT_BOLD, command=self._do_login).pack(fill="x", ipady=8)
            
        else:
            tk.Label(self.form, text="Create Username", bg=CARD, fg=MUTED).pack(anchor="w")
            self.e_user = tk.Entry(self.form, bg="#1C2234", fg=TEXT, insertbackground=TEXT, relief="flat")
            self.e_user.pack(fill="x", ipady=5, pady=(0, 10))
            
            tk.Label(self.form, text="Create Password", bg=CARD, fg=MUTED).pack(anchor="w")
            self.e_pass = tk.Entry(self.form, bg="#1C2234", fg=TEXT, insertbackground=TEXT, relief="flat", show="*")
            self.e_pass.pack(fill="x", ipady=5, pady=(0, 10))
            
            tk.Label(self.form, text="Confirm Password", bg=CARD, fg=MUTED).pack(anchor="w")
            self.e_pass2 = tk.Entry(self.form, bg="#1C2234", fg=TEXT, insertbackground=TEXT, relief="flat", show="*")
            self.e_pass2.pack(fill="x", ipady=5, pady=(0, 20))
            
            make_button(self.form, text="Next: Setup PIN", bg=ACCENT2, fg=BG, relief="flat", font=FONT_BOLD, command=self._do_register).pack(fill="x", ipady=8)

    def _do_login(self):
        u, p, pin = self.e_user.get().strip(), self.e_pass.get().strip(), self.e_pin.get().strip()
        if db.verify_login(u, p, pin):
            self.master.current_user = u
            self.master.show_frame(DashboardScreen)
        else:
            self.err_lbl.config(text="Invalid credentials or PIN.")

    def _do_register(self):
        u, p, p2 = self.e_user.get().strip(), self.e_pass.get().strip(), self.e_pass2.get().strip()
        if not u or not p:
            return self.err_lbl.config(text="Fields cannot be empty.")
        if p != p2:
            return self.err_lbl.config(text="Passwords do not match.")
        if db.user_exists(u):
            return self.err_lbl.config(text="Username already exists.")
        
        if db.register_user(u, p):
            self.master.current_user = u
            # One-time PIN setup flow
            pin = tk.simpledialog.askstring("PIN Setup", "Create a 4-digit Security PIN:", show="*")
            if pin and len(pin) == 4 and pin.isdigit():
                db.setup_pin(u, pin)
                messagebox.showinfo("Success", "Account created! Welcome to Safewheel.")
                self.master.show_frame(DashboardScreen)
            else:
                self.err_lbl.config(text="PIN setup failed. Please use a 4-digit PIN.")

class DashboardScreen(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG)
        self.master = master
        self._build()
        self.refresh_data()

    def _build(self):
        # Top Bar
        top = tk.Frame(self, bg=CARD, height=60)
        top.pack(fill="x")
        tk.Label(top, text="Safewheel Dashboard", bg=CARD, fg=TEXT, font=FONT_H1).pack(side="left", padx=20)
        make_button(top, text="Logout", bg=CARD, fg=DANGER, relief="flat", command=lambda: self.master.show_frame(AuthScreen)).pack(side="right", padx=20)
        
        # Main Content
        content = tk.Frame(self, bg=BG, padx=20, pady=20)
        content.pack(fill="both", expand=True)
        
        # Stat Cards
        stats_frame = tk.Frame(content, bg=BG)
        stats_frame.pack(fill="x", pady=(0, 20))
        
        self.lbl_income = self._stat_card(stats_frame, "TOTAL INCOME", ACCENT2)
        self.lbl_expense = self._stat_card(stats_frame, "TOTAL EXPENSES", DANGER)
        self.lbl_balance = self._stat_card(stats_frame, "NET BALANCE", ACCENT)
        
        # Split View: Table (Left) & Insights/Pet (Right)
        split = tk.Frame(content, bg=BG)
        split.pack(fill="both", expand=True)
        
        # Left: Table
        left = tk.Frame(split, bg=CARD, padx=15, pady=15)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        tk.Label(left, text="Transaction History", bg=CARD, fg=TEXT, font=FONT_BOLD).pack(anchor="w")
        
        self.tree = ttk.Treeview(left, columns=("Date", "Type", "Category", "Amount"), show="headings")
        for col in ("Date", "Type", "Category", "Amount"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.pack(fill="both", expand=True, pady=10)
        
        btn_box = tk.Frame(left, bg=CARD)
        btn_box.pack(fill="x")
        make_button(btn_box, text="+ Add Income", bg=ACCENT2, fg=BG, relief="flat", command=lambda: self.add_trans("Income")).pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=5)
        make_button(btn_box, text="+ Add Expense", bg=DANGER, fg=BG, relief="flat", command=lambda: self.add_trans("Expense")).pack(side="left", fill="x", expand=True, padx=(5, 0), ipady=5)
        make_button(btn_box, text="Delete", bg="#1C2234", fg=TEXT, relief="flat", command=self.delete_trans).pack(side="right", padx=(10, 0), ipady=5)

        # Right: Insights & Pet
        right = tk.Frame(split, bg=CARD, padx=15, pady=15)
        right.pack(side="right", fill="both", expand=True)
        
        tk.Label(right, text="Your Pet Assistant", bg=CARD, fg=TEXT, font=FONT_BOLD).pack(anchor="w")
        self.pet = AnimatedPet(right)
        self.pet.pack(pady=10)
        
        tk.Label(right, text="3D Data Analysis", bg=CARD, fg=TEXT, font=FONT_BOLD).pack(anchor="w", pady=(20, 5))
        if HAS_MPL:
            self.mpl_frame = tk.Frame(right, bg=CARD)
            self.mpl_frame.pack(fill="both", expand=True)
        else:
            tk.Label(right, text="Install matplotlib to view 3D charts.", bg=CARD, fg=MUTED).pack()

    def _stat_card(self, parent, title, color):
        card = tk.Frame(parent, bg=CARD, padx=15, pady=15)
        card.pack(side="left", fill="x", expand=True, padx=5)
        tk.Label(card, text=title, bg=CARD, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        lbl = tk.Label(card, text="₹0.00", bg=CARD, fg=color, font=FONT_STAT)
        lbl.pack(anchor="w")
        return lbl

    def refresh_data(self):
        # Update Stats
        inc, exp, bal = db.get_summary(self.master.current_user)
        self.lbl_income.config(text=f"₹{inc:,.2f}")
        self.lbl_expense.config(text=f"₹{exp:,.2f}")
        self.lbl_balance.config(text=f"₹{bal:,.2f}", fg=ACCENT2 if bal >= 0 else DANGER)
        
        # Update Table
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in db.get_transactions(self.master.current_user):
            self.tree.insert("", "end", iid=row["id"], values=(row["date"], row["type"], row["category"], f"₹{row['amount']:,.2f}"))
            
        # Update Chart
        if HAS_MPL:
            self._draw_3d_chart()

    def _draw_3d_chart(self):
        for w in self.mpl_frame.winfo_children():
            w.destroy()
            
        trans = db.get_transactions(self.master.current_user)
        if not trans:
            tk.Label(self.mpl_frame, text="No data for 3D analysis.", bg=CARD, fg=MUTED).pack()
            return

        # Group by Category
        cats = {}
        for t in trans:
            if t["type"] == "Expense":
                cats[t["category"]] = cats.get(t["category"], 0) + t["amount"]
                
        if not cats:
            tk.Label(self.mpl_frame, text="Add expenses to see 3D breakdown.", bg=CARD, fg=MUTED).pack()
            return

        fig = Figure(figsize=(5, 4), dpi=100, facecolor=CARD)
        ax = fig.add_subplot(111, projection='3d')
        ax.set_facecolor(CARD)
        
        labels = list(cats.keys())
        amounts = list(cats.values())
        xpos = np.arange(len(labels))
        ypos = np.zeros(len(labels))
        
        dx = np.ones(len(labels)) * 0.5
        dy = np.ones(len(labels)) * 0.5
        dz = amounts
        
        colors = ['#7C5CFF', '#22E0B8', '#FF5D6C', '#FFB84D', '#4DB8FF']
        ax.bar3d(xpos, ypos, np.zeros(len(labels)), dx, dy, dz, color=colors[:len(labels)], shade=True)
        
        ax.set_xticks(xpos + dx/2)
        ax.set_xticklabels(labels, color=TEXT, fontsize=8)
        ax.set_yticks([])
        ax.set_zlabel('Amount (₹)', color=TEXT, fontsize=8)
        ax.tick_params(axis='z', colors=TEXT, labelsize=8)
        
        for spine in ax.spines.values():
            spine.set_color(MUTED)
        ax.xaxis.set_pane_color((0.08, 0.09, 0.11, 1.0))
        ax.yaxis.set_pane_color((0.08, 0.09, 0.11, 1.0))
        ax.zaxis.set_pane_color((0.08, 0.09, 0.11, 1.0))
        
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.mpl_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def add_trans(self, t_type):
        win = tk.Toplevel(self)
        win.title(f"Add {t_type}")
        win.geometry("300x350")
        win.configure(bg=BG)
        win.transient(self)
        win.grab_set()
        
        tk.Label(win, text=f"Amount (₹)", bg=BG, fg=MUTED).pack(pady=(15,5))
        e_amt = tk.Entry(win, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat")
        e_amt.pack(ipady=5)
        
        tk.Label(win, text="Category", bg=BG, fg=MUTED).pack(pady=(10,5))
        categories = ["Food", "Transport", "Shopping", "Bills", "Health", "Salary", "Other"] if t_type == "Expense" else ["Salary", "Business", "Investment", "Gift", "Other"]
        cb_cat = ttk.Combobox(win, values=categories, state="readonly")
        cb_cat.pack()
        
        tk.Label(win, text="Description", bg=BG, fg=MUTED).pack(pady=(10,5))
        e_desc = tk.Entry(win, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat")
        e_desc.pack(ipady=5)
        
        def save():
            try:
                amt = float(e_amt.get())
                cat = cb_cat.get()
                desc = e_desc.get()
                if not cat: return messagebox.showerror("Error", "Select a category.")
                db.add_transaction(self.master.current_user, t_type, cat, amt, desc)
                win.destroy()
                self.refresh_data()
            except ValueError:
                messagebox.showerror("Error", "Invalid amount.")
                
        make_button(win, text="Save Transaction", bg=ACCENT, fg=TEXT, relief="flat", command=save).pack(pady=20, fill="x", padx=20, ipady=5)

    def delete_trans(self):
        sel = self.tree.selection()
        if not sel: return
        if messagebox.askyesno("Confirm", "Delete selected transaction?"):
            db.delete_transaction(sel[0])
            self.refresh_data()

if __name__ == "__main__":
    import tkinter.simpledialog
    app = App()
    app.mainloop()