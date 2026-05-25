# ============================================================
#  📊 成绩分析仪表板  |  dashboard.py
#  运行方式：streamlit run dashboard.py
#  依赖安装：pip install streamlit plotly pandas
# ============================================================
import streamlit as st
import json
import os
import datetime
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


# ──────────────────────────────────────────────────────────
#  1. 页面配置（必须是脚本中第一条 Streamlit 语句）
# ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="成绩分析仪表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ──────────────────────────────────────────────────────────
#  2. 全局自定义样式
# ──────────────────────────────────────────────────────────
st.markdown("""
<style>
/* 隐藏 Streamlit 默认菜单与页脚 */
#MainMenu, footer { visibility: hidden; }

/* 渐变横幅 */
.hero {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #06b6d4 100%);
    border-radius: 20px;
    padding: 32px 40px;
    color: white;
    margin-bottom: 28px;
}
.hero h1 { margin: 0; font-size: 2rem; font-weight: 700; letter-spacing: -0.5px; }
.hero p  { margin: 8px 0 0; opacity: 0.88; font-size: 1.05rem; }

/* KPI 指标卡片 */
.kpi {
    background: white;
    border-radius: 16px;
    padding: 24px 16px;
    text-align: center;
    border: 1px solid #e2e8f0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.10); }
.kpi .icon  { font-size: 2.2rem; }
.kpi .value { font-size: 2.1rem; font-weight: 700; color: #1e293b; margin: 6px 0 2px; }
.kpi .label { font-size: 0.82rem; color: #64748b; }

/* 排名页进度条 */
.bar-bg   { background: #f1f5f9; border-radius: 8px; height: 14px;
             overflow: hidden; margin-top: 12px; }
.bar-fill { height: 100%; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
#  3. 数据层（沿用第 9 课的 OOP 设计）
# ──────────────────────────────────────────────────────────

class Student:
    """学生类：封装姓名、学号与各科成绩"""

    def __init__(self, name: str, student_id: str):
        self.name        = name
        self.student_id  = student_id
        self.scores: dict[str, int] = {}
        self.created_at  = datetime.date.today().isoformat()

    def add_score(self, subject: str, score: int):
        if not (0 <= score <= 100):
            raise ValueError(f"成绩须在 0～100，收到：{score}")
        self.scores[subject] = score

    def average(self) -> float:
        return round(sum(self.scores.values()) / len(self.scores), 1) if self.scores else 0.0

    def grade(self) -> str:
        avg = self.average()
        if avg >= 90: return "A"
        if avg >= 75: return "B"
        if avg >= 60: return "C"
        return "D"

    def grade_label(self) -> str:
        return {"A": "优秀 ⭐", "B": "良好 ✅", "C": "及格 📝", "D": "待提高 ❌"}[self.grade()]

    def to_dict(self) -> dict:
        return {
            "name": self.name, "student_id": self.student_id,
            "scores": self.scores, "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict):
        s = cls(d["name"], d["student_id"])
        s.scores     = d.get("scores", {})
        s.created_at = d.get("created_at", "")
        return s


class GradeBook:
    """成绩册：管理所有学生，支持 JSON 持久化"""

    DATA_FILE = "gradebook.json"

    def __init__(self, class_name: str = "我的班级"):
        self.class_name = class_name
        self._students: dict[str, Student] = {}

    # ── CRUD ──────────────────────────────────────────────

    def add_student(self, name: str, student_id: str) -> tuple[bool, str]:
        if student_id in self._students:
            return False, f"学号 {student_id} 已存在"
        self._students[student_id] = Student(name, student_id)
        return True, f"已添加学生：{name}（{student_id}）"

    def add_score(self, student_id: str, subject: str, score: int) -> tuple[bool, str]:
        s = self._students.get(student_id)
        if not s:
            return False, f"找不到学号 {student_id}"
        try:
            s.add_score(subject, score)
            return True, f"已录入：{s.name} · {subject} · {score} 分"
        except ValueError as e:
            return False, str(e)

    # ── 查询 & 统计 ────────────────────────────────────────

    def all_students(self) -> list[Student]:
        return list(self._students.values())

    def with_scores(self) -> list[Student]:
        return [s for s in self._students.values() if s.scores]

    def class_average(self) -> float:
        ws = self.with_scores()
        return round(sum(s.average() for s in ws) / len(ws), 1) if ws else 0.0

    def pass_rate(self) -> float:
        ws = self.with_scores()
        if not ws: return 0.0
        return round(sum(1 for s in ws if s.average() >= 60) / len(ws) * 100, 1)

    def all_subjects(self) -> list[str]:
        subjects: set[str] = set()
        for s in self._students.values():
            subjects.update(s.scores.keys())
        return sorted(subjects)

    def subject_averages(self) -> dict[str, float]:
        result = {}
        for subj in self.all_subjects():
            vals = [s.scores[subj] for s in self._students.values() if subj in s.scores]
            if vals:
                result[subj] = round(sum(vals) / len(vals), 1)
        return result

    def to_dataframe(self) -> pd.DataFrame:
        subjects = self.all_subjects()
        rows = []
        for rank, s in enumerate(
            sorted(self.with_scores(), key=lambda x: x.average(), reverse=True), 1
        ):
            row = {"排名": rank, "学号": s.student_id, "姓名": s.name,
                   "均分": s.average(), "等级": s.grade_label()}
            for subj in subjects:
                row[subj] = s.scores.get(subj, "—")
            rows.append(row)
        return pd.DataFrame(rows)

    # ── 持久化 ────────────────────────────────────────────

    def save(self):
        data = {
            "class_name": self.class_name,
            "saved_at":   datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "students":   [s.to_dict() for s in self._students.values()],
        }
        with open(self.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls) -> "GradeBook":
        if not os.path.exists(cls.DATA_FILE):
            return cls()
        try:
            with open(cls.DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            gb = cls(data.get("class_name", "我的班级"))
            for sd in data.get("students", []):
                s = Student.from_dict(sd)
                gb._students[s.student_id] = s
            return gb
        except Exception:
            return cls()

    def __len__(self) -> int:
        return len(self._students)


# ──────────────────────────────────────────────────────────
#  4. Session State 初始化
#     Streamlit 每次交互都会重新执行脚本，
#     st.session_state 是唯一能跨次运行保持数据的地方。
# ──────────────────────────────────────────────────────────
if "gb" not in st.session_state:
    st.session_state.gb = GradeBook.load()

gb: GradeBook = st.session_state.gb    # 简写，方便后续引用

# 等级对应的颜色
GRADE_COLORS = {"A": "#34d399", "B": "#60a5fa", "C": "#fbbf24", "D": "#f87171"}


# ──────────────────────────────────────────────────────────
#  5. 侧边栏
# ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 成绩仪表板")
    st.divider()

    class_input = st.text_input("班级名称", value=gb.class_name)
    if class_input != gb.class_name:
        gb.class_name = class_input

    st.divider()
    page = st.radio(
        "页面导航",
        ["🏠  首页总览", "➕  录入成绩", "📈  数据分析", "🏆  学生排名"],
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("💾  保存数据", use_container_width=True, type="primary"):
        gb.save()
        st.success("✅ 数据已保存！")

    # 显示上次保存时间
    if os.path.exists(GradeBook.DATA_FILE):
        try:
            with open(GradeBook.DATA_FILE, encoding="utf-8") as _f:
                _saved = json.load(_f).get("saved_at", "")
            if _saved:
                st.caption(f"上次保存：{_saved}")
        except Exception:
            pass

    st.markdown("""
    <div style='text-align:center;margin-top:32px;opacity:0.38;font-size:0.72rem;line-height:2'>
    Python 基础（从零起飞）<br>第 10 课 · 阶段项目
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
#  辅助：渲染 KPI 卡片
# ──────────────────────────────────────────────────────────
def kpi_card(col, icon: str, value: str, label: str):
    with col:
        st.markdown(f"""
        <div class="kpi">
            <div class="icon">{icon}</div>
            <div class="value">{value}</div>
            <div class="label">{label}</div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  页面 A：🏠 首页总览
# ══════════════════════════════════════════════════════════
if "首页" in page:

    # 渐变横幅
    st.markdown(f"""
    <div class="hero">
        <h1>📊 {gb.class_name} · 成绩仪表板</h1>
        <p>实时掌握班级学情，数据驱动教与学</p>
    </div>
    """, unsafe_allow_html=True)

    ws   = gb.with_scores()
    best = max(ws, key=lambda s: s.average()) if ws else None

    # KPI 四格
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "👨‍🎓", str(len(gb)),              "在册学生数")
    kpi_card(c2, "📈",  str(gb.class_average()),   "班级均分")
    kpi_card(c3, "🏆",  best.name if best else "—",
             f"最高分 · {best.average() if best else 0}")
    kpi_card(c4, "✅",  f"{gb.pass_rate()}%",       "及格率")

    st.markdown("<br>", unsafe_allow_html=True)

    if ws:
        col_l, col_r = st.columns([3, 2])

        # 均分横向条形图
        with col_l:
            st.markdown("#### 学生均分一览")
            sorted_ws = sorted(ws, key=lambda s: s.average())
            fig_bar = px.bar(
                x=[s.average() for s in sorted_ws],
                y=[s.name      for s in sorted_ws],
                orientation="h",
                color=[s.average() for s in sorted_ws],
                color_continuous_scale=["#f87171", "#fbbf24", "#34d399"],
                range_color=[0, 100],
                text=[s.average() for s in sorted_ws],
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(
                xaxis_title=None, yaxis_title=None,
                coloraxis_showscale=False,
                margin=dict(l=0, r=20, t=10, b=0),
                height=max(260, len(ws) * 52),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(range=[0, 115], showgrid=True, gridcolor="#f1f5f9"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # 等级分布饼图
        with col_r:
            st.markdown("#### 等级分布")
            label_map   = {"A": "优秀", "B": "良好", "C": "及格", "D": "待提高"}
            grade_counts = {v: 0 for v in label_map.values()}
            for s in ws:
                grade_counts[label_map[s.grade()]] += 1

            fig_pie = px.pie(
                names=list(grade_counts.keys()),
                values=list(grade_counts.values()),
                color=list(grade_counts.keys()),
                color_discrete_map={
                    "优秀": "#34d399", "良好": "#60a5fa",
                    "及格": "#fbbf24", "待提高": "#f87171",
                },
                hole=0.45,
            )
            fig_pie.update_traces(
                textposition="inside", textinfo="percent+label",
                pull=[0.03] * 4,
            )
            fig_pie.update_layout(
                showlegend=False,
                margin=dict(l=0, r=0, t=10, b=0),
                height=310,
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.info("📭 还没有成绩数据。前往「➕ 录入成绩」页面添加学生和成绩吧！")


# ══════════════════════════════════════════════════════════
#  页面 B：➕ 录入成绩
# ══════════════════════════════════════════════════════════
elif "录入" in page:
    st.markdown("## ➕ 录入成绩")

    tab_stu, tab_score = st.tabs(["🧑 添加学生", "📝 录入科目成绩"])

    # ── 标签页 1：添加学生 ────────────────────────────────
    with tab_stu:
        st.markdown("#### 新增学生")
        with st.form("add_student", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("姓名", placeholder="例：小明")
            sid  = c2.text_input("学号", placeholder="例：S001")
            if st.form_submit_button("✅ 添加", type="primary", use_container_width=True):
                if name and sid:
                    ok, msg = gb.add_student(name.strip(), sid.strip())
                    (st.success if ok else st.error)(msg)
                    if ok:
                        gb.save()
                else:
                    st.warning("请填写姓名和学号")

        all_stu = gb.all_students()
        if all_stu:
            st.markdown("#### 当前学生名单")
            df_list = pd.DataFrame([
                {"学号": s.student_id, "姓名": s.name, "已录科目数": len(s.scores)}
                for s in all_stu
            ])
            st.dataframe(df_list, use_container_width=True, hide_index=True)

    # ── 标签页 2：录入成绩 ────────────────────────────────
    with tab_score:
        all_stu = gb.all_students()
        if not all_stu:
            st.info("请先在「添加学生」标签页添加学生。")
        else:
            st.markdown("#### 录入科目成绩")
            options = {f"{s.name}（{s.student_id}）": s.student_id for s in all_stu}
            with st.form("add_score", clear_on_submit=True):
                selected = st.selectbox("选择学生", list(options.keys()))
                c1, c2   = st.columns(2)
                subject  = c1.text_input("科目名称", placeholder="例：数学")
                score    = c2.number_input("成绩（0～100）", min_value=0, max_value=100, value=80)
                if st.form_submit_button("📥 录入", type="primary", use_container_width=True):
                    if subject:
                        ok, msg = gb.add_score(options[selected], subject.strip(), int(score))
                        (st.success if ok else st.error)(msg)
                        if ok:
                            gb.save()
                    else:
                        st.warning("请填写科目名称")

            # 已录入成绩预览（可折叠）
            st.markdown("#### 已录入成绩预览")
            for s in all_stu:
                if s.scores:
                    with st.expander(f"📋 {s.name}（均分 {s.average()} · {s.grade_label()}）"):
                        metric_cols = st.columns(min(len(s.scores), 6))
                        for j, (subj, sc) in enumerate(s.scores.items()):
                            metric_cols[j % 6].metric(
                                subj, f"{sc} 分",
                                f"{sc - 60:+d} 分" if sc != 60 else "±0",
                                delta_color="normal" if sc >= 60 else "inverse",
                            )


# ══════════════════════════════════════════════════════════
#  页面 C：📈 数据分析
# ══════════════════════════════════════════════════════════
elif "分析" in page:
    st.markdown("## 📈 数据分析")
    ws = gb.with_scores()

    if not ws:
        st.info("📭 还没有成绩数据，请先录入成绩。")
    else:
        subj_avg = gb.subject_averages()
        subjects = gb.all_subjects()

        # ── 各科平均分柱状图 ──────────────────────────────
        if subj_avg:
            st.markdown("#### 各科目平均分")
            df_sub = pd.DataFrame({
                "科目": list(subj_avg.keys()),
                "平均分": list(subj_avg.values()),
            })
            fig_sub = px.bar(
                df_sub, x="科目", y="平均分",
                color="平均分",
                color_continuous_scale=["#f87171", "#fbbf24", "#34d399"],
                range_color=[0, 100],
                text="平均分",
            )
            fig_sub.add_hline(y=60, line_dash="dash", line_color="#f87171",
                              annotation_text="及格线 60",
                              annotation_position="top right")
            fig_sub.add_hline(y=90, line_dash="dot", line_color="#34d399",
                              annotation_text="优秀线 90",
                              annotation_position="top right")
            fig_sub.update_traces(textposition="outside")
            fig_sub.update_layout(
                coloraxis_showscale=False,
                yaxis=dict(range=[0, 115], showgrid=True, gridcolor="#f1f5f9"),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=30, b=0, l=0, r=0), height=360,
            )
            st.plotly_chart(fig_sub, use_container_width=True)

        # ── 多科目雷达图（≥3 科 & ≥2 人时显示）─────────────
        if len(subjects) >= 3 and len(ws) >= 2:
            st.markdown("#### 多科目能力雷达（前 5 名）")
            top5   = sorted(ws, key=lambda s: s.average(), reverse=True)[:5]
            colors = ["#6366f1", "#f43f5e", "#10b981", "#f59e0b", "#06b6d4"]
            fig_r  = go.Figure()
            for i, s in enumerate(top5):
                vals = [s.scores.get(subj, 0) for subj in subjects]
                vals.append(vals[0])   # 首尾相连，闭合雷达图
                fig_r.add_trace(go.Scatterpolar(
                    r=vals,
                    theta=subjects + [subjects[0]],
                    fill="toself",
                    name=s.name,
                    line_color=colors[i % 5],
                    fillcolor=colors[i % 5],
                    opacity=0.18,
                ))
            fig_r.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                margin=dict(t=40, b=0, l=30, r=30),
                height=420,
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_r, use_container_width=True)

        # ── 各科成绩箱线图（≥2 科时显示）───────────────────
        if len(subjects) >= 2:
            st.markdown("#### 各科成绩分布（箱线图）")
            rows = [
                {"学生": s.name, "科目": subj, "成绩": sc}
                for s in ws
                for subj, sc in s.scores.items()
            ]
            fig_box = px.box(
                pd.DataFrame(rows), x="科目", y="成绩",
                color="科目",
                points="all",
                hover_data=["学生"],
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig_box.add_hline(y=60, line_dash="dash", line_color="#f87171",
                              annotation_text="及格线")
            fig_box.update_layout(
                showlegend=False,
                yaxis=dict(range=[0, 105], showgrid=True, gridcolor="#f1f5f9"),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10, b=0, l=0, r=0), height=360,
            )
            st.plotly_chart(fig_box, use_container_width=True)


# ══════════════════════════════════════════════════════════
#  页面 D：🏆 学生排名
# ══════════════════════════════════════════════════════════
elif "排名" in page:
    st.markdown("## 🏆 学生排名")
    ws = gb.with_scores()

    if not ws:
        st.info("📭 还没有成绩数据，请先录入成绩。")
    else:
        ranked = sorted(ws, key=lambda s: s.average(), reverse=True)
        medal  = ["🥇", "🥈", "🥉"]

        for i, s in enumerate(ranked):
            rank_icon = medal[i] if i < 3 else f"**# {i + 1}**"
            color     = GRADE_COLORS[s.grade()]

            col_r, col_n, col_bar, col_v = st.columns([1, 2, 5, 1])

            col_r.markdown(
                f"<div style='font-size:1.5rem;text-align:center;padding-top:10px'>"
                f"{rank_icon}</div>",
                unsafe_allow_html=True,
            )
            col_n.markdown(
                f"**{s.name}**  \n"
                f"<span style='color:#94a3b8;font-size:0.78rem'>{s.student_id}</span>",
                unsafe_allow_html=True,
            )
            col_bar.markdown(
                f'<div class="bar-bg">'
                f'<div class="bar-fill" style="width:{s.average()}%;background:{color}"></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            col_v.markdown(
                f"<div style='text-align:right;padding-top:10px;"
                f"font-weight:700;font-size:1.1rem;color:{color}'>{s.average()}</div>",
                unsafe_allow_html=True,
            )

            # 点击展开：各科成绩详情
            with st.expander(f"📋 {s.name} · {s.grade_label()} · 各科明细"):
                if s.scores:
                    detail_cols = st.columns(min(len(s.scores), 6))
                    for j, (subj, sc) in enumerate(s.scores.items()):
                        detail_cols[j % 6].metric(
                            subj, f"{sc}",
                            f"{sc - 60:+d}",
                            delta_color="normal" if sc >= 60 else "inverse",
                        )

        # 完整成绩表格
        st.divider()
        st.markdown("#### 完整成绩表")
        df_full = gb.to_dataframe()
        st.dataframe(
            df_full,
            use_container_width=True,
            hide_index=True,
            column_config={
                "均分": st.column_config.ProgressColumn(
                    "均分", min_value=0, max_value=100, format="%.1f",
                ),
                "等级": st.column_config.TextColumn("等级"),
            },
        )