# -*- coding: utf-8 -*-
"""用 Pillow 绘制 lxp.c 的程序流程图（2 倍超采样 + LANCZOS 缩放抗锯齿）"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

S = 2                                  # 超采样倍数
FONT_PATH = r'C:\Windows\Fonts\simhei.ttf'
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

PROC = ('#EAF2FB', '#2F6DB5')          # 处理
DEC = ('#FFF6E5', '#D0841A')           # 判断
TERM = ('#E9F6EA', '#2E7D32')          # 起止
SUB = ('#F4ECFB', '#6A3FA0')           # 子程序
IO = ('#FDECEF', '#B23A48')            # 输入输出
NOTE = ('#F5F5F5', '#9A9A9A')          # 说明
TXT = '#16202B'
ARROW = '#39434F'
KIND_STYLE = {'proc': PROC, 'dec': DEC, 'term': TERM, 'sub': SUB, 'io': IO, 'note': NOTE}


class Fig:
    def __init__(self, w, h):
        self.W, self.H = w, h
        self.im = Image.new('RGB', (w * S, h * S), 'white')
        self.d = ImageDraw.Draw(self.im)

    # ---------------- 文字 ----------------
    def _font(self, size):
        return ImageFont.truetype(FONT_PATH, max(8, int(round(size * S))))

    def _fit(self, lines, size, maxw, maxh):
        while size > 9:
            f = self._font(size)
            wmax = max(self.d.textlength(t, font=f) for t in lines) / S
            hh = len(lines) * size * 1.32 + (len(lines) - 1) * 5
            if wmax <= maxw and hh <= maxh:
                break
            size -= 1
        return size

    def text(self, cx, cy, lines, size=15, maxw=10 ** 9, maxh=10 ** 9, color=TXT):
        if isinstance(lines, str):
            lines = [lines]
        size = self._fit(lines, size, maxw, maxh)
        f = self._font(size)
        self.d.multiline_text((cx * S, cy * S), '\n'.join(lines), font=f, fill=color,
                              anchor='mm', align='center', spacing=int(5 * S))

    def ltext(self, x, cy, lines, size=14, maxw=10 ** 9, maxh=10 ** 9, color=TXT):
        """左对齐多行文字，x 为左边界"""
        if isinstance(lines, str):
            lines = [lines]
        size = self._fit(lines, size, maxw, maxh)
        f = self._font(size)
        self.d.multiline_text((x * S, cy * S), '\n'.join(lines), font=f, fill=color,
                              anchor='lm', align='left', spacing=int(5 * S))

    def title(self, s, y=36):
        f = self._font(25)
        self.d.text((self.W * S / 2, y * S), s, font=f, fill='#0E1A26', anchor='mm')

    def tag(self, cx, cy, s, size=13, color='#1A1A1A'):
        f = self._font(size)
        tw = self.d.textlength(s, font=f) / S
        th = size * 1.15
        pad = 3
        self.d.rectangle([(cx - tw / 2 - pad) * S, (cy - th / 2 - pad) * S,
                          (cx + tw / 2 + pad) * S, (cy + th / 2 + pad) * S], fill='white')
        self.d.text((cx * S, cy * S), s, font=f, fill=color, anchor='mm')

    # ---------------- 图形 ----------------
    def box(self, kind, cx, cy, w, h, lines, size=15):
        fill, edge = KIND_STYLE[kind]
        x0, y0 = (cx - w / 2) * S, (cy - h / 2) * S
        x1, y1 = (cx + w / 2) * S, (cy + h / 2) * S
        if kind == 'dec':
            self.d.polygon([(cx * S, y0), (x1, cy * S), (cx * S, y1), (x0, cy * S)],
                           fill=fill, outline=edge, width=2 * S)
            self.text(cx, cy, lines, size, maxw=w * 0.55, maxh=h * 0.52)
        elif kind == 'term':
            self.d.rounded_rectangle([x0, y0, x1, y1], radius=h / 2 * S,
                                     fill=fill, outline=edge, width=2 * S)
            self.text(cx, cy, lines, size, maxw=w - 22, maxh=h - 10)
        elif kind == 'io':
            sk = h * 0.22
            self.d.polygon([(x0 + sk * S, y0), (x1, y0), (x1 - sk * S, y1), (x0, y1)],
                           fill=fill, outline=edge, width=2 * S)
            self.text(cx, cy, lines, size, maxw=w - 2 * sk - 14, maxh=h - 10)
        else:
            r = 9 * S if kind != 'note' else 5 * S
            self.d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill,
                                     outline=edge, width=2 * S)
            if kind == 'sub':
                self.d.line([(cx - w / 2 + 10) * S, y0 + 3 * S, (cx - w / 2 + 10) * S, y1 - 3 * S],
                            fill=edge, width=S)
                self.d.line([(cx + w / 2 - 10) * S, y0 + 3 * S, (cx + w / 2 - 10) * S, y1 - 3 * S],
                            fill=edge, width=S)
            self.text(cx, cy, lines, size, maxw=w - (46 if kind == 'sub' else 26), maxh=h - 10)

    def note(self, cx, cy, w, h, lines, size=14, head=None):
        """说明框：左对齐文字"""
        self.box('note', cx, cy, w, h, [''], size)
        self.ltext(cx - w / 2 + 20, cy, lines, size,
                   maxw=w - 40, maxh=h - 16,
                   color='#33393F')
        if head:
            f = self._font(14)
            self.d.text(((cx - w / 2 + 20) * S, (cy - h / 2 + 12) * S), head,
                        font=f, fill='#6A6A6A', anchor='lm')

    def circle(self, cx, cy, r, label):
        self.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S],
                       fill='#FFFFFF', outline=ARROW, width=2 * S)
        self.text(cx, cy, label, 14)

    def dot(self, cx, cy, r=5):
        self.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S],
                       fill=ARROW, outline=ARROW)

    # ---------------- 箭头 ----------------
    def _seg(self, a, b, w, color, dash=None):
        if dash is None:
            self.d.line([a, b], fill=color, width=w)
            return
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L == 0:
            return
        ux, uy = dx / L, dy / L
        t, on = 0.0, True
        while t < L:
            step = min(dash[0] if on else dash[1], L - t)
            if on:
                self.d.line([(a[0] + ux * t, a[1] + uy * t),
                             (a[0] + ux * (t + step), a[1] + uy * (t + step))],
                            fill=color, width=w)
            t += step
            on = not on

    def _head(self, a, b, color):
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        L = 12 * S
        Wd = 5.5 * S
        base = (b[0] - L * math.cos(ang), b[1] - L * math.sin(ang))
        left = (base[0] - Wd * math.sin(ang), base[1] + Wd * math.cos(ang))
        right = (base[0] + Wd * math.sin(ang), base[1] - Wd * math.cos(ang))
        self.d.polygon([b, left, right], fill=color)

    def arrow(self, pts, label=None, lpos=None, dashed=False, color=ARROW, width=2, head=True):
        p = [(x * S, y * S) for x, y in pts]
        dash = (7 * S, 5 * S) if dashed else None
        for i in range(len(p) - 1):
            self._seg(p[i], p[i + 1], width * S, color, dash)
        if head and len(p) >= 2:
            self._head(p[-2], p[-1], color)
        if label:
            lx, ly = lpos if lpos else ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
            self.tag(lx, ly, label)

    def save(self, name):
        path = os.path.join(OUT_DIR, name)
        self.im.resize((self.W, self.H), Image.LANCZOS).save(path, 'PNG')
        print('saved', path, self.W, 'x', self.H)


# ---------------- 通用节点 ----------------
def node(fig, kind, cx, cy, w, h, lines, size=15):
    lines = lines if isinstance(lines, list) else [lines]
    fig.box(kind, cx, cy, w, h, lines, size)
    return {'cx': cx, 'cy': cy, 'w': w, 'h': h, 'top': cy - h / 2, 'bot': cy + h / 2}


def vlink(fig, a, b, **kw):
    fig.arrow([(a['cx'], a['bot']), (b['cx'], b['top'])], **kw)


# ======================= 图 1：主程序 =======================
def build_main():
    f = Fig(1560, 1700)
    f.title('智能小车主程序流程图（lxp.c · AT89C52）')
    X = 620

    t = node(f, 'term', X, 95, 240, 56, ['上电复位 / 开始'])
    p1 = node(f, 'proc', X, 190, 430, 76, ['初始化 GPIO：P1.0~P1.5 输出低电平',
                                           'P2.0~P2.5 置 1 作输入，模式灯灭'])
    p2 = node(f, 'proc', X, 290, 430, 76, ['sreceiver_init()：串口方式 1，REN=1',
                                           'Timer1 方式 2 自动重装 → 9600bps'])
    p3 = node(f, 'proc', X, 390, 430, 76, ['gettimer0_init(T0_1MS)：Timer0 方式 1',
                                           '1ms 中断 → 10 分度软件 PWM（100Hz）'])
    p4 = node(f, 'proc', X, 480, 430, 56, ['get_sum_timer1(0)：计时器复位'])
    p5 = node(f, 'proc', X, 570, 430, 76, ['INT0/INT1 下降沿触发，开 EX0/EX1',
                                           'mode_flag = 0（蓝牙模式），EA = 1'])
    for a, b in [(t, p1), (p1, p2), (p2, p3), (p3, p4), (p4, p5)]:
        vlink(f, a, b)

    f.arrow([(X, p5['bot']), (X, 640)])
    f.circle(X, 660, 20, 'A')
    k = node(f, 'sub', X, 745, 330, 66, ['key_scan()  按键扫描'])
    f.arrow([(X, 680), (X, k['top'])])

    d = node(f, 'dec', X, 885, 350, 124, ['mode_flag == 0 ?', '（蓝牙模式？）'])
    vlink(f, k, d)

    # ---- 是：蓝牙模式 ----
    a1 = node(f, 'io', 260, 1035, 330, 76, ['receiver_data()：查询串口',
                                            '等 0xAA 帧头，收 4 字节'])
    a2 = node(f, 'proc', 260, 1155, 330, 86, ['set_motion() / car_stop()',
                                              '修改 speed_cur 与电机方向'])
    f.arrow([(X - d['w'] / 2, 885), (260, 885), (260, a1['top'])], label='是', lpos=(360, 862))
    vlink(f, a1, a2)

    # ---- 否：巡线模式 ----
    b1 = node(f, 'io', 1150, 1035, 360, 76, ['line_scan()：读 P2.0~P2.4',
                                             '5 路红外判断偏差'])
    b2 = node(f, 'proc', 1150, 1155, 360, 86, ['set_motion()',
                                               '按偏差改左右轮速度与方向'])
    f.arrow([(X + d['w'] / 2, 885), (1150, 885), (1150, b1['top'])], label='否', lpos=(900, 862))
    vlink(f, b1, b2)

    # ---- 汇合后返回主循环 ----
    f.arrow([(1150, b2['bot']), (1150, 1310)])
    f.arrow([(260, a2['bot']), (260, 1310), (1500, 1310), (1500, 745), (k['cx'] + k['w'] / 2, 745)])
    f.tag(1010, 1288, '返回主循环：每轮重新判断模式、刷新一次速度')

    # ---- 图例 ----
    f.text(112, 1404, ['图例'], 17, color='#3A3A3A')
    legend = [('term', '起止（程序入口 / 出口）'), ('proc', '处理（赋值、初始化、调用）'),
              ('dec', '判断（分支、循环）'), ('io', '输入 / 输出（子程序调用）'),
              ('sub', '子程序（被主程序调用）')]
    y = 1448
    for kind, label in legend:
        f.box(kind, 130, y, 92, 30, [''], 12)
        f.ltext(192, y, [label], 14, maxw=470)
        y += 46

    f.note(1160, 1520, 620, 210,
           ['主循环不阻塞：PWM 由 Timer0 中断持续输出，主程序',
            '只负责改 speed_cur 和 motor_dir，所以按键、蓝牙不会',
            '打断 PWM。',
            '',
            '按键只在外部中断里置标志，消抖和动作在 key_scan() 里做；',
            '蓝牙 / 巡线两种模式由 mode_flag 切换，切换时先停车。'], 14,
           head='说明')
    f.save('主程序流程图.png')


# ======================= 图 2：中断与按键 =======================
def build_isr():
    f = Fig(2150, 1080)
    f.title('中断服务程序与按键流程图（lxp.c · AT89C52）')

    # ---------- Timer0 中断 ----------
    t = node(f, 'term', 340, 95, 300, 56, ['Timer0 中断（每 1ms）'])
    p1 = node(f, 'proc', 340, 190, 380, 58, ['重装 TH0/TL0（初值 65536-921）'])
    p2 = node(f, 'proc', 340, 280, 380, 58, ['base_timer0++（PWM 分度 +1）'])
    d1 = node(f, 'dec', 340, 395, 320, 104, ['base_timer0 ≥ 10 ?'])
    for a, b in [(t, p1), (p1, p2)]:
        vlink(f, a, b)
    vlink(f, p2, d1)

    q = node(f, 'proc', 110, 480, 180, 54, ['base_timer0 = 0'], 13)
    f.arrow([(340 - d1['w'] / 2, 395), (110, 395), (110, q['top'])], label='是', lpos=(222, 373))
    f.arrow([(110, q['bot']), (110, 572), (340, 572)], head=False)
    f.dot(340, 572)

    p3 = node(f, 'proc', 340, 660, 400, 64, ['pwm_init(&speed_cur, base_timer0)'])
    f.arrow([(340, d1['bot']), (340, p3['top'])], label='否', lpos=(374, 610))
    n1 = node(f, 'note', 800, 660, 340, 104,
              ['按 motor_dir 摆好 4 个方向脚；', 'pwm_num < speed 则 PWM 脚输出高，',
               '否则输出低（10 分度 = 100Hz）'], 13)
    f.arrow([(340 + p3['w'] / 2, 660), (n1['cx'] - n1['w'] / 2, 660)], dashed=True)

    p4 = node(f, 'proc', 340, 775, 400, 58, ['ms_tick++（毫秒节拍）'])
    vlink(f, p3, p4)
    rt = node(f, 'term', 340, 875, 240, 56, ['中断返回'])
    vlink(f, p4, rt)

    # ---------- 外部中断 ----------
    t2 = node(f, 'term', 1120, 95, 340, 56, ['INT0 / INT1 外部中断'])
    e1 = node(f, 'proc', 1120, 200, 380, 76, ['key1_flag = 1（选择键）', 'key2_flag = 1（确认键）'])
    e2 = node(f, 'proc', 1120, 315, 380, 64, ['关 EX0 / EX1，防止抖动重复触发'])
    e3 = node(f, 'term', 1120, 420, 240, 56, ['中断返回'])
    for a, b in [(t2, e1), (e1, e2), (e2, e3)]:
        vlink(f, a, b)
    n2 = node(f, 'note', 1120, 570, 400, 132,
              ['按键低电平有效、下降沿触发；', '中断里只置标志、马上返回，',
               '真正的消抖和动作在 key_scan() 里做，', '这样不会长时间占用中断。'], 13)
    f.arrow([(1120, e3['bot']), (1120, n2['top'])], dashed=True)

    # ---------- key_scan ----------
    t3 = node(f, 'term', 1710, 95, 260, 56, ['key_scan()'])
    f.text(1520, 268, ['选择键：只挑模式'], 13, color='#6A3FA0')
    f.text(1900, 268, ['确认键：让模式生效'], 13, color='#6A3FA0')
    f.arrow([(1710, t3['bot']), (1710, 205), (1520, 205), (1520, 292)])
    f.arrow([(1710, 205), (1900, 205), (1900, 292)])

    dA1 = node(f, 'dec', 1520, 340, 320, 96, ['key1_flag == 1 ?'])
    dA2 = node(f, 'proc', 1520, 455, 330, 58, ['systim_delay(10) 消抖'])
    dA3 = node(f, 'dec', 1520, 565, 320, 96, ['KEY_SEL == 0 ?'])
    dA4 = node(f, 'proc', 1520, 680, 330, 58, ['mode_sel 取反（0↔1）'])
    dA5 = node(f, 'proc', 1520, 785, 330, 58, ['key1_flag = 0；EX0 = 1'])
    vlink(f, dA1, dA2, label='是', lpos=(1558, 402))
    vlink(f, dA2, dA3, label='是', lpos=(1558, 508))
    vlink(f, dA3, dA4, label='是', lpos=(1558, 620))
    vlink(f, dA4, dA5)

    dB1 = node(f, 'dec', 1900, 340, 320, 96, ['key2_flag == 1 ?'])
    dB2 = node(f, 'proc', 1900, 455, 330, 58, ['systim_delay(10) 消抖'])
    dB3 = node(f, 'dec', 1900, 565, 320, 96, ['KEY_OK == 0 ?'])
    dB4 = node(f, 'dec', 1900, 685, 320, 100, ['mode_sel ≠ mode_flag ?'])
    dB5 = node(f, 'proc', 1900, 810, 340, 76, ['mode_flag = mode_sel；car_stop()',
                                               '更新模式指示灯'], 14)
    dB6 = node(f, 'proc', 1900, 915, 330, 58, ['key2_flag = 0；EX1 = 1'])
    vlink(f, dB1, dB2, label='是', lpos=(1862, 402))
    vlink(f, dB2, dB3, label='是', lpos=(1862, 508))
    vlink(f, dB3, dB4, label='是', lpos=(1862, 626))
    vlink(f, dB4, dB5, label='是', lpos=(1862, 745))
    vlink(f, dB5, dB6)

    # 否 分支汇合到中间通道（只汇合，不再加箭头，避免两个箭头对撞）
    lane = 1710
    f.arrow([(dA1['cx'] + dA1['w'] / 2, 340), (lane, 340)], head=False)
    f.arrow([(dA3['cx'] + dA3['w'] / 2, 565), (lane, 565)], head=False)
    f.arrow([(dB1['cx'] - dB1['w'] / 2, 340), (lane, 340)], head=False)
    f.arrow([(dB3['cx'] - dB3['w'] / 2, 565), (lane, 565)], head=False)
    f.arrow([(dB4['cx'] - dB4['w'] / 2, 685), (lane, 685)], head=False)
    f.tag(1674, 320, '否')
    f.tag(1674, 545, '否')
    f.tag(1746, 320, '否')
    f.tag(1746, 545, '否')
    f.tag(1746, 665, '否')

    rk = node(f, 'term', 1710, 1000, 240, 56, ['返回 main()'])
    f.arrow([(lane, 340), (lane, rk['top'])])
    f.arrow([(1520, dA5['bot']), (1520, 1000), (rk['cx'] - rk['w'] / 2, 1000)])
    f.arrow([(1900, dB6['bot']), (1900, 1000), (rk['cx'] + rk['w'] / 2, 1000)])
    f.save('中断与按键流程图.png')


# ======================= 图 3：蓝牙接收 + 巡线 =======================
def build_sub():
    f = Fig(1900, 1400)
    f.title('蓝牙接收与巡线流程图（lxp.c · AT89C52）')

    # ---------- receiver_data() ----------
    X1 = 560
    t = node(f, 'term', X1, 95, 300, 56, ['receiver_data()'])
    p1 = node(f, 'proc', X1, 190, 470, 58, ['get_sum_timer1(20)：启动 20ms 超时'])
    p2 = node(f, 'proc', X1, 282, 470, 58, ['等待 RI = 1（20ms 超时则返回 0）'])
    p3 = node(f, 'proc', X1, 372, 470, 58, ['redata[0] = SBUF；RI = 0'])
    d1 = node(f, 'dec', X1, 478, 330, 100, ['redata[0] == 0xAA ?'], 14)
    r1 = node(f, 'term', 930, 478, 250, 56, ['返回 0（帧头不对）'], 14)
    p4 = node(f, 'proc', X1, 585, 470, 54, ['i = 1（开始收后 3 个字节）'], 14)

    for a, b in [(t, p1), (p1, p2), (p2, p3), (p3, d1)]:
        vlink(f, a, b)
    f.arrow([(d1['cx'] + d1['w'] / 2, 478), (r1['cx'] - r1['w'] / 2, 478)], label='否', lpos=(770, 456))
    vlink(f, d1, p4, label='是', lpos=(600, 542))

    # ---- 收后 3 字节的循环 ----
    dy = 700
    d2 = node(f, 'dec', X1, dy, 310, 96, ['i ≤ 3 ?'], 14)
    f.dot(X1, 632)
    f.arrow([(X1, 612), (X1, 632)])
    f.arrow([(X1, 632), (X1, d2['top'])])

    b1 = node(f, 'proc', 250, 800, 300, 58, ['等待 RI = 1（超时返回 0）'], 13)
    b2 = node(f, 'proc', 250, 886, 300, 58, ['redata[i] = SBUF；RI = 0'], 13)
    b3 = node(f, 'proc', 250, 962, 300, 50, ['i++'], 13)
    f.arrow([(d2['cx'] - d2['w'] / 2, dy), (250, dy), (250, b1['top'])], label='是', lpos=(330, 678))
    vlink(f, b1, b2)
    vlink(f, b2, b3)
    # 循环回到 i ≤ 3 之前
    f.arrow([(250, b3['bot']), (250, 1030), (60, 1030), (60, 632), (X1, 632)], head=False)

    d3 = node(f, 'dec', X1, 1080, 340, 100, ['redata[1] 是 0x00~0x04 ?'], 14)
    r2 = node(f, 'term', 940, 1080, 250, 56, ['返回 0（命令非法）'], 14)
    f.arrow([(X1, d2['bot']), (X1, d3['top'])], label='否', lpos=(600, 800))
    f.arrow([(d3['cx'] + d3['w'] / 2, 1080), (r2['cx'] - r2['w'] / 2, 1080)], label='否', lpos=(780, 1058))
    a1 = node(f, 'proc', X1, 1190, 470, 66, ['car_stop() / set_motion()', '按命令与速度更新 speed_cur、motor_dir'], 14)
    t1 = node(f, 'term', X1, 1275, 220, 54, ['返回 1'])
    vlink(f, d3, a1, label='是', lpos=(600, 1148))
    vlink(f, a1, t1)

    # ---------- line_scan() ----------
    X2, AX, LANE = 1330, 1670, 1840
    t2 = node(f, 'term', X2, 95, 260, 56, ['line_scan()'])
    q1 = node(f, 'proc', X2, 195, 430, 72, ['读 P2 低 5 位，按 LINE_BLACK 取反得 s',
                                            '（1 = 该路压在黑线上）'], 14)
    c1 = node(f, 'dec', X2, 308, 340, 96, ['s == 0x00 ?（丢线）'], 14)
    c2 = node(f, 'dec', X2, 422, 340, 96, ['s & 0x01 ?（最左）'], 14)
    c3 = node(f, 'dec', X2, 536, 340, 96, ['s & 0x10 ?（最右）'], 14)
    c4 = node(f, 'dec', X2, 650, 340, 96, ['s & 0x02 ?（偏左）'], 14)
    c5 = node(f, 'dec', X2, 764, 340, 96, ['s & 0x08 ?（偏右）'], 14)
    q2 = node(f, 'proc', X2, 875, 430, 64, ['都不是：中间 0x04，直行'], 14)
    rt = node(f, 'term', X2, 975, 330, 56, ['返回（PWM 由中断持续输出）'], 14)

    vlink(f, t2, q1)
    vlink(f, q1, c1)
    f.arrow([(X2, c1['bot']), (X2, c2['top'])], label='否', lpos=(X2 + 36, 370))
    f.arrow([(X2, c2['bot']), (X2, c3['top'])], label='否', lpos=(X2 + 36, 484))
    f.arrow([(X2, c3['bot']), (X2, c4['top'])], label='否', lpos=(X2 + 36, 598))
    f.arrow([(X2, c4['bot']), (X2, c5['top'])], label='否', lpos=(X2 + 36, 712))
    vlink(f, c5, q2, label='否', lpos=(X2 + 36, 826))
    vlink(f, q2, rt)

    r0 = node(f, 'proc', AX, 308, 300, 64, ['保持上一次速度 / 方向', '直接返回'], 13)
    ra = node(f, 'proc', AX, 422, 300, 72, ['原地左转', '左轮反转，右轮正转'], 13)
    rb = node(f, 'proc', AX, 536, 300, 72, ['原地右转', '左轮正转，右轮反转'], 13)
    rc = node(f, 'proc', AX, 650, 300, 72, ['左轮减速，右轮全速', '（向右修正）'], 13)
    rd = node(f, 'proc', AX, 764, 300, 72, ['右轮减速，左轮全速', '（向左修正）'], 13)

    for c, r in [(c1, r0), (c2, ra), (c3, rb), (c4, rc), (c5, rd)]:
        f.arrow([(c['cx'] + c['w'] / 2, c['cy']), (r['cx'] - r['w'] / 2, c['cy'])],
                label='是', lpos=(c['cx'] + c['w'] / 2 + 18, c['cy'] - 22))

    # 右侧汇合通道：各修正分支 -> set_motion -> 返回
    for r in (ra, rb, rc, rd):
        f.arrow([(r['cx'] + r['w'] / 2, r['cy']), (LANE, r['cy'])], head=False)
    f.arrow([(LANE, 422), (LANE, 975), (rt['cx'] + rt['w'] / 2, 975)])
    f.note(X2, 1110, 470, 96, ['五个 是 分支最后都调 set_motion() 改 speed_cur',
                               '和 motor_dir；丢线时保持上一次动作不改变。'], 13)
    f.save('蓝牙与巡线流程图.png')


if __name__ == '__main__':
    build_main()
    build_isr()
    build_sub()
