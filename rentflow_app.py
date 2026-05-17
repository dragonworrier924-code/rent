import streamlit as st
import json
import uuid
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="RentFlow — ভাড়া ম্যানেজমেন্ট",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  GLOBAL CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans Bengali', sans-serif;
}

/* dark background */
[data-testid="stAppViewContainer"] {
    background: #0a0b0f;
    color: #eef0f8;
}
[data-testid="stSidebar"] {
    background: #13151d !important;
    border-right: 1px solid #252836;
}
[data-testid="stSidebar"] * { color: #eef0f8 !important; }

/* metric cards */
[data-testid="metric-container"] {
    background: #13151d;
    border: 1px solid #252836;
    border-radius: 14px;
    padding: 18px 20px 14px !important;
}
[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 800 !important; }
[data-testid="stMetricLabel"] { font-size: 11px !important; font-weight: 700 !important; color: #4d5270 !important; text-transform: uppercase; letter-spacing: 0.8px; }

/* dataframe */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* buttons */
.stButton > button {
    border-radius: 9px !important;
    font-weight: 700 !important;
    font-family: 'Noto Sans Bengali', sans-serif !important;
}

/* form inputs */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stDateInput > div > div > input,
.stSelectbox > div > div > div {
    background: #1a1d28 !important;
    border: 1.5px solid #2e3245 !important;
    border-radius: 9px !important;
    color: #eef0f8 !important;
}

/* section headers */
h1, h2, h3 { color: #eef0f8 !important; }

/* expander */
[data-testid="stExpander"] {
    background: #13151d !important;
    border: 1px solid #252836 !important;
    border-radius: 12px !important;
}

/* tabs */
[data-testid="stTabs"] button {
    font-weight: 700 !important;
    font-family: 'Noto Sans Bengali', sans-serif !important;
}

div[data-testid="stHorizontalBlock"] {
    gap: 12px;
}

/* success/error message boxes */
.stSuccess, .stError, .stInfo, .stWarning {
    border-radius: 10px !important;
}

/* hide default streamlit footer */
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────
UTIL_TYPES = [
    ("💡", "বিদ্যুৎ বিল"),
    ("🔥", "গ্যাস বিল"),
    ("💧", "পানির বিল"),
    ("🌐", "ইন্টারনেট বিল"),
    ("🧹", "ময়লা/সার্ভিস চার্জ"),
    ("🛗", "লিফট চার্জ"),
    ("🔒", "নিরাপত্তা চার্জ"),
    ("📋", "অন্যান্য"),
]
PAYMENT_METHODS = ["নগদ", "বিকাশ", "নগদ (মোবাইল)", "ব্যাংক ট্রান্সফার", "রকেট", "অন্যান্য"]

STORE_KEY = "rentflow_db"

# ─────────────────────────────────────────────
#  SESSION STATE / PERSISTENCE
# ─────────────────────────────────────────────
def init_db():
    if "db" not in st.session_state:
        st.session_state.db = {"tenants": [], "payments": [], "utilities": []}

def get_db():
    return st.session_state.db

def save_db():
    pass  # Streamlit session_state persists during session; for file persistence use below

def new_id():
    return str(uuid.uuid4())[:8]

init_db()
db = get_db()

# ─────────────────────────────────────────────
#  CALCULATIONS
# ─────────────────────────────────────────────
def months_passed(move_in_str: str) -> int:
    d = datetime.strptime(move_in_str, "%Y-%m-%d").date()
    now = date.today()
    if d > now:
        return 0
    diff = (now.year - d.year) * 12 + (now.month - d.month) + 1
    return max(1, diff)

def calc_tenant(t: dict) -> dict:
    months   = months_passed(t["move_in"])
    expected = months * t["rent"]
    paid     = sum(p["amount"] for p in db["payments"] if p["tenant_id"] == t["id"])
    utils    = sum(u["amount"] for u in db["utilities"] if u["tenant_id"] == t["id"])
    prev     = t.get("prev_balance", 0)
    due      = expected + utils + prev - paid
    return {**t, "months": months, "expected": expected, "paid": paid, "utils": utils, "due": due}

def global_stats():
    twb      = [calc_tenant(t) for t in db["tenants"]]
    monthly  = sum(t["rent"] for t in db["tenants"])
    dues     = sum(t["due"] for t in twb if t["due"] > 0)
    collected= sum(p["amount"] for p in db["payments"])
    util_tot = sum(u["amount"] for u in db["utilities"])
    return twb, monthly, dues, collected, util_tot

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def fmt_bn(n: float) -> str:
    """Format number with Bengali numerals."""
    bn_digits = "০১২৩৪৫৬৭৮৯"
    s = f"{int(round(n)):,}"
    return "".join(bn_digits[int(c)] if c.isdigit() else c for c in s)

def fmt_date_bn(d_str: str) -> str:
    if not d_str:
        return "—"
    try:
        d = datetime.strptime(d_str, "%Y-%m-%d")
        months_bn = ["জানু","ফেব্রু","মার্চ","এপ্রিল","মে","জুন",
                     "জুলাই","আগস্ট","সেপ্ট","অক্টো","নভে","ডিসে"]
        return f"{fmt_bn(d.day)} {months_bn[d.month-1]} {fmt_bn(d.year)}"
    except:
        return d_str

def badge_html(text, color):
    colors = {
        "red":    ("#f87171","rgba(248,113,113,0.12)","rgba(248,113,113,0.3)"),
        "green":  ("#34d399","rgba(52,211,153,0.08)","rgba(52,211,153,0.25)"),
        "amber":  ("#fbbf24","rgba(251,191,36,0.08)","rgba(251,191,36,0.25)"),
        "blue":   ("#60a5fa","rgba(96,165,250,0.08)","rgba(96,165,250,0.25)"),
        "purple": ("#a78bfa","rgba(124,111,247,0.12)","rgba(124,111,247,0.3)"),
    }
    fg, bg, brd = colors.get(color, colors["purple"])
    return (f'<span style="display:inline-flex;align-items:center;padding:3px 10px;'
            f'border-radius:20px;font-size:12px;font-weight:700;'
            f'color:{fg};background:{bg};border:1px solid {brd};">'
            f'{text}</span>')

def metric_card(label, value, color="#eef0f8", sub=""):
    return f"""
<div style="background:#13151d;border:1px solid #252836;border-radius:14px;
            padding:20px 22px 16px;margin-bottom:0;">
  <div style="font-size:10.5px;font-weight:700;color:#4d5270;text-transform:uppercase;
              letter-spacing:0.8px;margin-bottom:10px;">{label}</div>
  <div style="font-size:28px;font-weight:800;letter-spacing:-1px;color:{color};line-height:1;
              margin-bottom:6px;">৳{fmt_bn(value)}</div>
  {f'<div style="font-size:12px;color:#4d5270;">{sub}</div>' if sub else ''}
</div>"""

def section_header(title):
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;margin:28px 0 16px;">
  <h3 style="font-size:16px;font-weight:800;white-space:nowrap;margin:0;">{title}</h3>
  <div style="flex:1;height:1px;background:#252836;"></div>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="display:flex;align-items:center;gap:12px;padding:8px 0 20px;">
  <div style="width:44px;height:44px;background:linear-gradient(135deg,#7c6ff7,#a78bfa);
              border-radius:11px;display:flex;align-items:center;justify-content:center;
              font-size:22px;box-shadow:0 4px 16px rgba(124,111,247,0.4);">🏠</div>
  <div>
    <div style="font-size:20px;font-weight:800;letter-spacing:-0.5px;">
      Rent<span style="background:linear-gradient(135deg,#7c6ff7,#a78bfa);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;">Flow</span>
    </div>
    <div style="font-size:10px;font-weight:700;color:#4d5270;letter-spacing:1px;">ভাড়া ম্যানেজমেন্ট</div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    _, monthly, dues, collected, _ = global_stats()
    twb_all = [calc_tenant(t) for t in db["tenants"]]

    st.markdown(f"""
<div style="background:#1a1d28;border:1px solid #252836;border-radius:9px;padding:12px 14px;margin-bottom:8px;">
  <div style="font-size:10px;font-weight:700;color:#4d5270;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px;">মাসিক ভাড়া রোল</div>
  <div style="font-size:20px;font-weight:800;color:#eef0f8;">৳{fmt_bn(monthly)}</div>
</div>
<div style="background:#1a1d28;border:1px solid #252836;border-radius:9px;padding:12px 14px;margin-bottom:8px;">
  <div style="font-size:10px;font-weight:700;color:#4d5270;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px;">মোট বকেয়া</div>
  <div style="font-size:20px;font-weight:800;color:#f87171;">৳{fmt_bn(dues)}</div>
</div>
<div style="background:#1a1d28;border:1px solid #252836;border-radius:9px;padding:12px 14px;margin-bottom:16px;">
  <div style="font-size:10px;font-weight:700;color:#4d5270;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px;">মোট আদায়</div>
  <div style="font-size:20px;font-weight:800;color:#34d399;">৳{fmt_bn(collected)}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("**মূল মেনু**")
    page = st.radio(
        "নেভিগেশন",
        ["🏠 ড্যাশবোর্ড", "👥 ভাড়াটিয়া", "💳 পেমেন্ট হিস্ট্রি", "⚡ ইউটিলিটি বিল", "📊 রিপোর্ট"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown(f"""<div style="font-size:12px;color:#4d5270;text-align:center;">
        ভাড়াটিয়া: <b style="color:#a78bfa">{len(db['tenants'])}</b> &nbsp;|&nbsp;
        পেমেন্ট: <b style="color:#34d399">{len(db['payments'])}</b> &nbsp;|&nbsp;
        ইউটিলিটি: <b style="color:#fbbf24">{len(db['utilities'])}</b>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  QUICK ACTION BAR (top)
# ─────────────────────────────────────────────
col_t, col_p, col_u = st.columns([1, 1, 1])

with col_t:
    add_tenant_btn = st.button("➕ নতুন ভাড়াটিয়া", use_container_width=True, type="primary")
with col_p:
    add_payment_btn = st.button("💰 পেমেন্ট রেকর্ড", use_container_width=True)
with col_u:
    add_utility_btn = st.button("⚡ ইউটিলিটি বিল", use_container_width=True)

# open state flags
if "show_tenant_form" not in st.session_state:
    st.session_state.show_tenant_form = False
if "show_payment_form" not in st.session_state:
    st.session_state.show_payment_form = False
if "show_utility_form" not in st.session_state:
    st.session_state.show_utility_form = False
if "preselect_tenant" not in st.session_state:
    st.session_state.preselect_tenant = None

if add_tenant_btn:
    st.session_state.show_tenant_form = not st.session_state.show_tenant_form
    st.session_state.show_payment_form = False
    st.session_state.show_utility_form = False

if add_payment_btn:
    st.session_state.show_payment_form = not st.session_state.show_payment_form
    st.session_state.show_tenant_form = False
    st.session_state.show_utility_form = False
    st.session_state.preselect_tenant = None

if add_utility_btn:
    st.session_state.show_utility_form = not st.session_state.show_utility_form
    st.session_state.show_tenant_form = False
    st.session_state.show_payment_form = False
    st.session_state.preselect_tenant = None

# ─────────────────────────────────────────────
#  ADD TENANT FORM
# ─────────────────────────────────────────────
if st.session_state.show_tenant_form:
    st.markdown("---")
    st.markdown("### 🏠 নতুন ভাড়াটিয়া যোগ করুন")
    with st.form("tenant_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name    = c1.text_input("পুরো নাম *", placeholder="যেমন: মোহাম্মদ রহিম")
        unit    = c2.text_input("ইউনিট / ফ্ল্যাট *", placeholder="যেমন: ৪বি")
        c3, c4  = st.columns(2)
        rent    = c3.number_input("মাসিক ভাড়া (৳) *", min_value=0, value=0, step=500)
        move_in = c4.date_input("ভাড়া শুরুর তারিখ *", value=date.today())
        c5, c6  = st.columns(2)
        phone   = c5.text_input("ফোন নম্বর", placeholder="০১XXXXXXXXX")
        prev_bal= c6.number_input("পূর্বের বকেয়া (৳)", min_value=0, value=0)
        note    = st.text_input("ঠিকানা / নোট", placeholder="যেমন: ৩য় তলা")

        sub_col1, sub_col2 = st.columns([1, 4])
        submitted = sub_col1.form_submit_button("✅ সেভ করুন", type="primary", use_container_width=True)
        cancel    = sub_col2.form_submit_button("বাতিল", use_container_width=False)

        if submitted:
            if not name or not unit or rent <= 0:
                st.error("নাম, ইউনিট এবং ভাড়া অবশ্যই পূরণ করুন।")
            else:
                db["tenants"].append({
                    "id": new_id(),
                    "name": name, "unit": unit, "rent": float(rent),
                    "move_in": str(move_in),
                    "prev_balance": float(prev_bal),
                    "phone": phone, "note": note,
                    "created_at": datetime.now().isoformat(),
                })
                st.session_state.show_tenant_form = False
                st.success(f"✅ {name} সফলভাবে যোগ করা হয়েছে!")
                st.rerun()
        if cancel:
            st.session_state.show_tenant_form = False
            st.rerun()

# ─────────────────────────────────────────────
#  ADD PAYMENT FORM
# ─────────────────────────────────────────────
if st.session_state.show_payment_form:
    st.markdown("---")
    st.markdown("### 💳 পেমেন্ট রেকর্ড করুন")
    if not db["tenants"]:
        st.warning("প্রথমে একজন ভাড়াটিয়া যোগ করুন।")
    else:
        with st.form("payment_form", clear_on_submit=True):
            tenant_opts = {f"{t['name']} ({t['unit']})": t["id"] for t in db["tenants"]}

            pre = st.session_state.get("preselect_tenant")
            preselect_label = next((k for k, v in tenant_opts.items() if v == pre), None)
            default_idx = list(tenant_opts.keys()).index(preselect_label) if preselect_label else 0

            chosen_label = st.selectbox("ভাড়াটিয়া নির্বাচন *", list(tenant_opts.keys()), index=default_idx)
            tid = tenant_opts[chosen_label]

            c1, c2 = st.columns(2)
            amount   = c1.number_input("প্রাপ্ত পরিমাণ (৳) *", min_value=1, value=1, step=500)
            pay_date = c2.date_input("পেমেন্টের তারিখ *", value=date.today())
            c3, c4 = st.columns(2)
            method = c3.selectbox("পেমেন্ট পদ্ধতি", [""] + PAYMENT_METHODS)
            p_note = c4.text_input("নোট", placeholder="যেমন: জুলাই মাসের ভাড়া")

            sc1, sc2 = st.columns([1, 4])
            sub = sc1.form_submit_button("✅ রেকর্ড করুন", type="primary", use_container_width=True)
            cxl = sc2.form_submit_button("বাতিল")

            if sub:
                db["payments"].append({
                    "id": new_id(), "tenant_id": tid,
                    "amount": float(amount), "date": str(pay_date),
                    "method": method, "note": p_note,
                    "created_at": datetime.now().isoformat(),
                })
                st.session_state.show_payment_form = False
                st.session_state.preselect_tenant = None
                st.success("✅ পেমেন্ট রেকর্ড হয়েছে!")
                st.rerun()
            if cxl:
                st.session_state.show_payment_form = False
                st.rerun()

# ─────────────────────────────────────────────
#  ADD UTILITY FORM
# ─────────────────────────────────────────────
if st.session_state.show_utility_form:
    st.markdown("---")
    st.markdown("### ⚡ ইউটিলিটি বিল যোগ করুন")
    if not db["tenants"]:
        st.warning("প্রথমে একজন ভাড়াটিয়া যোগ করুন।")
    else:
        with st.form("utility_form", clear_on_submit=True):
            tenant_opts = {f"{t['name']} ({t['unit']})": t["id"] for t in db["tenants"]}
            pre = st.session_state.get("preselect_tenant")
            preselect_label = next((k for k, v in tenant_opts.items() if v == pre), None)
            default_idx = list(tenant_opts.keys()).index(preselect_label) if preselect_label else 0

            chosen_label = st.selectbox("ভাড়াটিয়া নির্বাচন *", list(tenant_opts.keys()), index=default_idx)
            tid = tenant_opts[chosen_label]
            u_date = st.date_input("বিলের তারিখ *", value=date.today())

            st.markdown("**ইউটিলিটি সমূহ (পরিমাণ লিখুন, খালি রাখলে যোগ হবে না)**")
            util_amounts = {}
            cols_per_row = 2
            util_list = list(enumerate(UTIL_TYPES))
            for row_start in range(0, len(util_list), cols_per_row):
                row = util_list[row_start:row_start + cols_per_row]
                cols = st.columns(cols_per_row)
                for col_idx, (i, (icon, label)) in enumerate(row):
                    val_u = cols[col_idx].number_input(f"{icon} {label}", min_value=0.0, value=0.0, step=10.0, key=f"util_{i}")
                    util_amounts[label] = val_u

            sc1, sc2 = st.columns([1, 4])
            sub = sc1.form_submit_button("✅ সেভ করুন", type="primary", use_container_width=True)
            cxl = sc2.form_submit_button("বাতিল")

            if sub:
                added = 0
                for label, amt in util_amounts.items():
                    if amt > 0:
                        db["utilities"].append({
                            "id": new_id(), "tenant_id": tid,
                            "description": label, "amount": float(amt),
                            "date": str(u_date),
                            "created_at": datetime.now().isoformat(),
                        })
                        added += 1
                if added == 0:
                    st.error("কমপক্ষে একটি ইউটিলিটির পরিমাণ দিন।")
                else:
                    st.session_state.show_utility_form = False
                    st.session_state.preselect_tenant = None
                    st.success(f"✅ {fmt_bn(added)}টি ইউটিলিটি বিল যোগ হয়েছে!")
                    st.rerun()
            if cxl:
                st.session_state.show_utility_form = False
                st.rerun()

st.markdown("---")

# ─────────────────────────────────────────────
#  PAGE: DASHBOARD
# ─────────────────────────────────────────────
if page == "🏠 ড্যাশবোর্ড":
    st.markdown("## 🏠 ড্যাশবোর্ড")
    twb, monthly, dues, collected, util_tot = global_stats()
    owing   = [t for t in twb if t["due"] > 0]
    cleared = [t for t in twb if t["due"] <= 0]

    # Stat cards row 1
    c1, c2, c3 = st.columns(3)
    c1.markdown(metric_card("💰 মাসিক ভাড়া রোল", monthly, "#a78bfa",
                            f"{len(db['tenants'])} জন ভাড়াটিয়া"), unsafe_allow_html=True)
    c2.markdown(metric_card("⚠️ মোট বকেয়া পাওনা", dues,
                            "#f87171" if dues > 0 else "#34d399",
                            f"{len(owing)} জনের কাছে বকেয়া"), unsafe_allow_html=True)
    c3.markdown(metric_card("✅ মোট আদায় (সর্বমোট)", collected, "#34d399",
                            f"{len(db['payments'])}টি পেমেন্ট রেকর্ড"), unsafe_allow_html=True)

    if db["tenants"]:
        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
        c4, c5, c6 = st.columns(3)
        c4.markdown(metric_card("⚡ মোট ইউটিলিটি বিল", util_tot, "#fbbf24",
                                f"{len(db['utilities'])}টি বিল এন্ট্রি"), unsafe_allow_html=True)
        avg_rent = monthly / len(db["tenants"]) if db["tenants"] else 0
        c5.markdown(metric_card("📊 গড় মাসিক ভাড়া", avg_rent, "#eef0f8",
                                "প্রতি ভাড়াটিয়া"), unsafe_allow_html=True)
        cleared_pct = len(cleared)
        c6.markdown(f"""
<div style="background:#13151d;border:1px solid #252836;border-radius:14px;padding:20px 22px 16px;">
  <div style="font-size:10.5px;font-weight:700;color:#4d5270;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:10px;">🏠 পরিশোধিত ভাড়াটিয়া</div>
  <div style="font-size:28px;font-weight:800;color:#34d399;line-height:1;margin-bottom:6px;">{fmt_bn(cleared_pct)}<span style="font-size:16px;color:#4d5270;"> / {fmt_bn(len(db['tenants']))}</span></div>
  <div style="font-size:12px;color:#4d5270;">{'সবাই পরিশোধিত 🎉' if len(owing)==0 else f'{fmt_bn(len(owing))} জনের বকেয়া বাকি'}</div>
</div>""", unsafe_allow_html=True)

    # Owing tenants table
    section_header("⚠️ বকেয়া ভাড়াটিয়া")
    if not owing:
        st.markdown("""
<div style="background:#13151d;border:1px solid #252836;border-radius:14px;
            padding:44px 20px;text-align:center;">
  <div style="font-size:40px;margin-bottom:12px;">🎉</div>
  <div style="font-size:16px;font-weight:700;color:#8b91b4;margin-bottom:6px;">দারুণ!</div>
  <div style="font-size:13px;color:#4d5270;">সব ভাড়াটিয়ার ভাড়া পরিশোধিত।</div>
</div>""", unsafe_allow_html=True)
    else:
        rows = []
        for t in owing:
            rows.append({
                "নাম": t["name"],
                "ইউনিট": t["unit"],
                "মাসিক ভাড়া": f"৳{fmt_bn(t['rent'])}",
                "মাস": fmt_bn(t["months"]),
                "মোট প্রত্যাশিত": f"৳{fmt_bn(t['expected'])}",
                "মোট পরিশোধ": f"৳{fmt_bn(t['paid'])}",
                "বকেয়া ৳": int(t["due"]),
                "ফোন": t.get("phone") or "—",
            })
        import pandas as pd
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={"বকেয়া ৳": st.column_config.NumberColumn("বকেয়া ৳", format="৳%d")})

    # Recent payments & utilities
    c_left, c_right = st.columns(2)
    with c_left:
        section_header("💳 সাম্প্রতিক পেমেন্ট")
        rec_pay = sorted(db["payments"], key=lambda x: x["created_at"], reverse=True)[:6]
        if not rec_pay:
            st.info("কোনো পেমেন্ট নেই।")
        else:
            for p in rec_pay:
                t = next((x for x in db["tenants"] if x["id"] == p["tenant_id"]), None)
                st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:12px 16px;border-bottom:1px solid #252836;">
  <div>
    <div style="font-weight:700;font-size:13.5px;">{t['name'] if t else '—'}</div>
    <div style="font-size:12px;color:#4d5270;">{t['unit'] if t else ''} • {fmt_date_bn(p['date'])}{' • '+p['method'] if p.get('method') else ''}</div>
  </div>
  {badge_html('+৳'+fmt_bn(p['amount']), 'green')}
</div>""", unsafe_allow_html=True)

    with c_right:
        section_header("⚡ সাম্প্রতিক ইউটিলিটি")
        rec_util = sorted(db["utilities"], key=lambda x: x["created_at"], reverse=True)[:6]
        if not rec_util:
            st.info("কোনো ইউটিলিটি নেই।")
        else:
            for u in rec_util:
                t = next((x for x in db["tenants"] if x["id"] == u["tenant_id"]), None)
                st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:12px 16px;border-bottom:1px solid #252836;">
  <div>
    <div style="font-weight:700;font-size:13.5px;">{t['name'] if t else '—'}</div>
    <div style="font-size:12px;color:#4d5270;">{u['description']} • {fmt_date_bn(u['date'])}</div>
  </div>
  {badge_html('৳'+fmt_bn(u['amount']), 'amber')}
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  PAGE: TENANTS
# ─────────────────────────────────────────────
elif page == "👥 ভাড়াটিয়া":
    st.markdown("## 👥 ভাড়াটিয়া")
    twb = [calc_tenant(t) for t in db["tenants"]]

    if not twb:
        st.markdown("""
<div style="background:#13151d;border:1px solid #252836;border-radius:14px;
            padding:60px 20px;text-align:center;margin:20px 0;">
  <div style="font-size:44px;margin-bottom:12px;">🏠</div>
  <div style="font-size:15px;font-weight:700;color:#8b91b4;margin-bottom:6px;">কোনো ভাড়াটিয়া নেই</div>
  <div style="font-size:13px;color:#4d5270;">উপরে "নতুন ভাড়াটিয়া" বাটনে ক্লিক করে শুরু করুন।</div>
</div>""", unsafe_allow_html=True)
    else:
        # Cards grid
        cols_per_row = 3
        for row_start in range(0, len(twb), cols_per_row):
            row = twb[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for col_idx, t in enumerate(row):
                with cols[col_idx]:
                    due_color = "#f87171" if t["due"] > 0 else ("#60a5fa" if t["due"] < 0 else "#34d399")
                    due_label = (f"৳{fmt_bn(t['due'])} বকেয়া" if t["due"] > 0
                                 else f"৳{fmt_bn(abs(t['due']))} অতিরিক্ত" if t["due"] < 0
                                 else "পরিশোধিত ✓")
                    due_badge_color = "red" if t["due"] > 0 else "blue" if t["due"] < 0 else "green"
                    border_accent = "#f87171" if t["due"] > 0 else "#60a5fa" if t["due"] < 0 else "#34d399"
                    initials = "".join(w[0] for w in t["name"].split())[:2].upper()

                    st.markdown(f"""
<div style="background:#13151d;border:1px solid #252836;border-left:3px solid {border_accent};
            border-radius:14px;padding:18px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
    <div style="display:flex;align-items:center;gap:10px;">
      <div style="width:40px;height:40px;border-radius:50%;
                  background:linear-gradient(135deg,#7c6ff7,#a78bfa);
                  display:flex;align-items:center;justify-content:center;
                  font-size:15px;font-weight:800;color:#fff;">{initials}</div>
      <div>
        <div style="font-size:15px;font-weight:700;">{t['name']}</div>
        <div style="font-size:12px;color:#4d5270;">{t['unit']}</div>
      </div>
    </div>
    {badge_html(due_label, due_badge_color)}
  </div>
  <div style="background:#1a1d28;border-radius:9px;padding:12px;margin-bottom:12px;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;">
      <div><div style="color:#4d5270;margin-bottom:3px;">মাসিক ভাড়া</div><div style="font-weight:700;">৳{fmt_bn(t['rent'])}</div></div>
      <div><div style="color:#4d5270;margin-bottom:3px;">অতিবাহিত মাস</div><div style="font-weight:700;color:#a78bfa;">{fmt_bn(t['months'])} মাস</div></div>
      <div><div style="color:#4d5270;margin-bottom:3px;">মোট পরিশোধ</div><div style="font-weight:700;color:#34d399;">৳{fmt_bn(t['paid'])}</div></div>
      <div><div style="color:#4d5270;margin-bottom:3px;">ইউটিলিটি</div><div style="font-weight:700;color:#fbbf24;">৳{fmt_bn(t['utils'])}</div></div>
    </div>
  </div>
  <div style="font-size:12px;color:#4d5270;margin-bottom:10px;">
    📅 {fmt_date_bn(t['move_in'])}
    {('&nbsp;📞 ' + t['phone']) if t.get('phone') else ''}
    {('&nbsp;⚠️ পূর্বের বকেয়া: ৳'+fmt_bn(t['prev_balance'])) if t.get('prev_balance',0)>0 else ''}
  </div>
</div>""", unsafe_allow_html=True)

                    # Action buttons
                    bc1, bc2, bc3 = st.columns(3)
                    with bc1:
                        if st.button("💰 পেমেন্ট", key=f"pay_{t['id']}", use_container_width=True):
                            st.session_state.show_payment_form = True
                            st.session_state.show_tenant_form = False
                            st.session_state.show_utility_form = False
                            st.session_state.preselect_tenant = t["id"]
                            st.rerun()
                    with bc2:
                        if st.button("⚡ ইউটিলিটি", key=f"util_{t['id']}", use_container_width=True):
                            st.session_state.show_utility_form = True
                            st.session_state.show_tenant_form = False
                            st.session_state.show_payment_form = False
                            st.session_state.preselect_tenant = t["id"]
                            st.rerun()
                    with bc3:
                        if st.button("🗑️ মুছুন", key=f"del_{t['id']}", use_container_width=True):
                            st.session_state[f"confirm_del_{t['id']}"] = True

                    if st.session_state.get(f"confirm_del_{t['id']}", False):
                        st.warning(f"⚠️ **{t['name']}** কে মুছে ফেলবেন? এই কাজ পূর্বাবস্থায় ফেরানো যাবে না।")
                        cc1, cc2 = st.columns(2)
                        if cc1.button("✅ হ্যাঁ, মুছুন", key=f"yes_del_{t['id']}", type="primary"):
                            db["tenants"]   = [x for x in db["tenants"]   if x["id"] != t["id"]]
                            db["payments"]  = [x for x in db["payments"]  if x["tenant_id"] != t["id"]]
                            db["utilities"] = [x for x in db["utilities"] if x["tenant_id"] != t["id"]]
                            del st.session_state[f"confirm_del_{t['id']}"]
                            st.success(f"{t['name']} মুছে ফেলা হয়েছে।")
                            st.rerun()
                        if cc2.button("❌ বাতিল", key=f"no_del_{t['id']}"):
                            del st.session_state[f"confirm_del_{t['id']}"]
                            st.rerun()

        # Detailed table
        section_header("📋 ভাড়াটিয়া তালিকা (বিস্তারিত)")
        import pandas as pd
        rows = []
        for t in twb:
            rows.append({
                "নাম": t["name"],
                "ইউনিট": t["unit"],
                "মাসিক ভাড়া": int(t["rent"]),
                "শুরুর তারিখ": fmt_date_bn(t["move_in"]),
                "মাস": int(t["months"]),
                "প্রত্যাশিত": int(t["expected"]),
                "পরিশোধ": int(t["paid"]),
                "ইউটিলিটি": int(t["utils"]),
                "বকেয়া": int(t["due"]),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={
                         "মাসিক ভাড়া": st.column_config.NumberColumn(format="৳%d"),
                         "প্রত্যাশিত":  st.column_config.NumberColumn(format="৳%d"),
                         "পরিশোধ":     st.column_config.NumberColumn(format="৳%d"),
                         "ইউটিলিটি":   st.column_config.NumberColumn(format="৳%d"),
                         "বকেয়া":      st.column_config.NumberColumn(format="৳%d"),
                     })

# ─────────────────────────────────────────────
#  PAGE: PAYMENTS
# ─────────────────────────────────────────────
elif page == "💳 পেমেন্ট হিস্ট্রি":
    st.markdown("## 💳 পেমেন্ট হিস্ট্রি")
    total = sum(p["amount"] for p in db["payments"])
    st.markdown(f"""
<div style="margin-bottom:16px;">
  {badge_html('মোট আদায়: ৳'+fmt_bn(total), 'green')}
  &nbsp;
  {badge_html(fmt_bn(len(db['payments']))+'টি পেমেন্ট', 'purple')}
</div>""", unsafe_allow_html=True)

    if not db["payments"]:
        st.info("কোনো পেমেন্ট রেকর্ড নেই। উপরে 'পেমেন্ট রেকর্ড' বাটনে ক্লিক করুন।")
    else:
        import pandas as pd
        sorted_pays = sorted(db["payments"], key=lambda x: x["date"], reverse=True)
        rows = []
        for p in sorted_pays:
            t = next((x for x in db["tenants"] if x["id"] == p["tenant_id"]), None)
            rows.append({
                "তারিখ": fmt_date_bn(p["date"]),
                "নাম": t["name"] if t else "—",
                "ইউনিট": t["unit"] if t else "—",
                "পদ্ধতি": p.get("method") or "—",
                "নোট": p.get("note") or "—",
                "পরিশোধিত ৳": int(p["amount"]),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={"পরিশোধিত ৳": st.column_config.NumberColumn(format="৳%d")})

# ─────────────────────────────────────────────
#  PAGE: UTILITIES
# ─────────────────────────────────────────────
elif page == "⚡ ইউটিলিটি বিল":
    st.markdown("## ⚡ ইউটিলিটি বিল")
    total_u = sum(u["amount"] for u in db["utilities"])
    st.markdown(f"""
<div style="margin-bottom:16px;">
  {badge_html('মোট বিল: ৳'+fmt_bn(total_u), 'amber')}
  &nbsp;
  {badge_html(fmt_bn(len(db['utilities']))+'টি এন্ট্রি', 'purple')}
</div>""", unsafe_allow_html=True)

    # Per-type breakdown cards
    if db["utilities"]:
        by_type = {}
        for icon, label in UTIL_TYPES:
            amt = sum(u["amount"] for u in db["utilities"] if u["description"] == label)
            if amt > 0:
                by_type[(icon, label)] = amt

        if by_type:
            cols_per_row = 4
            items = list(by_type.items())
            for row_start in range(0, len(items), cols_per_row):
                row = items[row_start:row_start + cols_per_row]
                cols = st.columns(cols_per_row)
                for ci, ((icon, label), amt) in enumerate(row):
                    cols[ci].markdown(f"""
<div style="background:#13151d;border:1px solid #252836;border-top:3px solid #fbbf24;
            border-radius:14px;padding:16px;margin-bottom:8px;">
  <div style="font-size:11px;font-weight:700;color:#4d5270;margin-bottom:8px;">{icon} {label}</div>
  <div style="font-size:22px;font-weight:800;color:#fbbf24;">৳{fmt_bn(amt)}</div>
</div>""", unsafe_allow_html=True)

    if not db["utilities"]:
        st.info("কোনো ইউটিলিটি বিল নেই। উপরে 'ইউটিলিটি বিল' বাটনে ক্লিক করুন।")
    else:
        section_header("📋 সকল ইউটিলিটি বিল")
        import pandas as pd
        sorted_utils = sorted(db["utilities"], key=lambda x: x["date"], reverse=True)
        rows = []
        for u in sorted_utils:
            t = next((x for x in db["tenants"] if x["id"] == u["tenant_id"]), None)
            rows.append({
                "তারিখ": fmt_date_bn(u["date"]),
                "নাম": t["name"] if t else "—",
                "ইউনিট": t["unit"] if t else "—",
                "বিবরণ": u["description"],
                "পরিমাণ ৳": int(u["amount"]),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={"পরিমাণ ৳": st.column_config.NumberColumn(format="৳%d")})

# ─────────────────────────────────────────────
#  PAGE: REPORT
# ─────────────────────────────────────────────
elif page == "📊 রিপোর্ট":
    st.markdown("## 📊 সারসংক্ষেপ রিপোর্ট")

    twb, monthly, dues, collected, util_tot = global_stats()
    total_expected = sum(t["expected"] for t in twb)
    collection_rate = round((collected / total_expected) * 100) if total_expected > 0 else 0

    today_str = date.today().strftime("%d %B %Y")
    st.markdown(f"<div style='font-size:13px;color:#4d5270;margin-bottom:20px;'>রিপোর্ট তৈরির তারিখ: {today_str}</div>", unsafe_allow_html=True)

    # KPI row
    c1, c2, c3 = st.columns(3)
    c1.markdown(metric_card("📊 মোট প্রত্যাশিত (সব সময়)", total_expected, "#a78bfa"), unsafe_allow_html=True)
    c2.markdown(metric_card("✅ মোট আদায়", collected, "#34d399"), unsafe_allow_html=True)
    rate_color = "#34d399" if collection_rate >= 80 else "#fbbf24" if collection_rate >= 50 else "#f87171"
    c3.markdown(f"""
<div style="background:#13151d;border:1px solid #252836;border-radius:14px;padding:20px 22px 16px;">
  <div style="font-size:10.5px;font-weight:700;color:#4d5270;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:10px;">📈 সংগ্রহ হার</div>
  <div style="font-size:28px;font-weight:800;color:{rate_color};line-height:1;margin-bottom:8px;">{fmt_bn(collection_rate)}%</div>
  <div style="height:6px;background:#252836;border-radius:10px;overflow:hidden;">
    <div style="height:100%;width:{min(collection_rate,100)}%;background:{rate_color};border-radius:10px;"></div>
  </div>
  <div style="font-size:12px;color:#4d5270;margin-top:6px;">প্রত্যাশিত বনাম আদায়</div>
</div>""", unsafe_allow_html=True)

    # Bar chart — last 6 months
    section_header("📊 মাসিক পেমেন্ট সংগ্রহ (সর্বশেষ ৬ মাস)")
    import pandas as pd
    month_names_bn = ["জানু","ফেব্রু","মার্চ","এপ্রিল","মে","জুন",
                      "জুলাই","আগস্ট","সেপ্ট","অক্টো","নভে","ডিসে"]
    now = date.today()
    chart_data = []
    for i in range(5, -1, -1):
        d = date(now.year, now.month, 1) - relativedelta(months=i)
        key = d.strftime("%Y-%m")
        amt = sum(p["amount"] for p in db["payments"] if p["date"].startswith(key))
        chart_data.append({"মাস": month_names_bn[d.month - 1], "আদায় (৳)": amt})
    chart_df = pd.DataFrame(chart_data).set_index("মাস")
    st.bar_chart(chart_df, use_container_width=True, height=250, color="#7c6ff7")

    # Per-tenant breakdown
    section_header("👥 ভাড়াটিয়া ভিত্তিক বিশ্লেষণ")
    if not twb:
        st.info("কোনো ভাড়াটিয়া নেই।")
    else:
        rows = []
        for t in twb:
            total_due_base = t["expected"] + t["utils"]
            rate = round((t["paid"] / total_due_base) * 100) if total_due_base > 0 else 100
            rows.append({
                "নাম": t["name"],
                "ইউনিট": t["unit"],
                "মোট প্রত্যাশিত": int(t["expected"]),
                "মোট পরিশোধ": int(t["paid"]),
                "ইউটিলিটি": int(t["utils"]),
                "নেট বকেয়া ৳": int(t["due"]),
                "সংগ্রহ হার %": min(rate, 100),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={
                         "মোট প্রত্যাশিত":    st.column_config.NumberColumn(format="৳%d"),
                         "মোট পরিশোধ":        st.column_config.NumberColumn(format="৳%d"),
                         "ইউটিলিটি":          st.column_config.NumberColumn(format="৳%d"),
                         "নেট বকেয়া ৳":       st.column_config.NumberColumn(format="৳%d"),
                         "সংগ্রহ হার %":       st.column_config.ProgressColumn(
                             "সংগ্রহ হার %", min_value=0, max_value=100, format="%d%%"),
                     })

        # Export CSV
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 CSV ডাউনলোড করুন",
            data=csv_bytes,
            file_name=f"rentflow_report_{date.today()}.csv",
            mime="text/csv",
        )
