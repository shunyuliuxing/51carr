//个人程序设计
/*==========================================================================
 *  51 智能小车完整程序（AT89C52：8KB Flash / 256B RAM；兼容 AT89C51）
 *  建议晶振 11.0592MHz（蓝牙 9600 才准）
 *--------------------------------------------------------------------------
 *  硬件资源分配（按手里的 L298N 双 H 桥 + 5 路红外 + HC-05/06 蓝牙）
 *    P1.0/P1.1   左电机方向 IN1/IN2        P1.2/P1.3   右电机方向 IN1/IN2
 *    P1.4/P1.5   左/右电机 PWM（ENA/ENB 使能脚）
 *    P2.0~P2.4   5 路红外巡线传感器，P2.0 最左，P2.4 最右
 *    P2.5        模式指示灯（可选，低电平点亮：灭=蓝牙模式 亮=巡线模式）
 *    P3.2/INT0   选择键（内部上拉，按键另一端接地，低电平有效）
 *    P3.3/INT1   确认键
 *    P3.0/P3.1   RXD/TXD 接蓝牙模块（9600bps）
 *
 *  定时器 / 中断分配
 *    Timer0  方式1，1ms 基准中断：10 分度软件 PWM（10ms=100Hz）+ 毫秒节拍
 *    Timer1  方式2，串口波特率发生器（9600bps），自动重装，不占中断
 *    Timer2  本程序不用（AT89C52 才有，留给你以后加蜂鸣器/硬件 PWM）
 *    中断 0  外部中断 0：选择键
 *    中断 1  外部中断 1：确认键
 *    中断 4  串口：本程序用查询方式收数据，见 sreceiver_init() 里的说明
 *
 *  蓝牙数据帧（4 字节，手机 APP 按此格式发）
 *    redata[0] = 0xAA     帧头
 *    redata[1] = 方向命令 0x00 停 0x01 前进 0x02 后退 0x03 原地左转 0x04 原地右转
 *    redata[2] = 左轮速度 0~10
 *    redata[3] = 右轮速度 0~10
 *
 *  相对原始注释骨架的微调（原因都写在对应函数里）
 *    1. 软件 PWM 放进 Timer0 中断里按 10 个分度循环，主循环只负责改速度，
 *       这样蓝牙接收、按键扫描都不会打断 PWM（原来的写法会在主循环里阻塞）。
 *    2. AT89C52 上 Timer0 做基准定时和软件 PWM、Timer1 必须留给串口做波特率，
 *       Timer2 本程序不用，所以“计时器”改用 Timer0 的毫秒节拍做倒计时，
 *       函数名和接口都不变（以后想省 CPU，可以把软件 PWM 换成 Timer2 的硬件输出）。
 *    3. key_scan()/line_scan()/sreceiver_init() 补上返回类型 void
 *       （原骨架没写返回类型，C51 会按 int 处理并报警告）。
 *    4. receiver_data() 里等数据加了超时，避免一直卡在 while(RI==0)。
 *=========================================================================*/
/* 原骨架写的是 <REGX52.H>（STC 风格的头文件），Keil 自带的 INC 里只有
   REG52.H，两者定义的 51/52 寄存器完全一样，AT89C52/AT89C51 都能直接用；
   你的 Keil 里如果有 REGX52.H，换回 <REGX52.H> 也一样能编译。 */
#include <REG52.H>

/* Keil C51 不一定带 stdint.h，这里直接 typedef，最省事也最稳 */
typedef unsigned char uint8_t;
typedef unsigned int  uint16_t;

/*------------------------------ 引脚定义 ------------------------------*/
/* 4 个 GPIO 通用输出用于控制正反转 + 2 个 PWM 输出 */
sbit M_L_IN1 = P1^0;            /* 左电机方向脚 1 */
sbit M_L_IN2 = P1^1;            /* 左电机方向脚 2 */
sbit M_R_IN1 = P1^2;            /* 右电机方向脚 1 */
sbit M_R_IN2 = P1^3;            /* 右电机方向脚 2 */
sbit M_L_PWM = P1^4;            /* 左电机 PWM（使能） */
sbit M_R_PWM = P1^5;            /* 右电机 PWM（使能） */

/* 5 路红外巡线传感器，5 个 GPIO 输入 */
sbit S_L2 = P2^0;               /* 最左 */
sbit S_L1 = P2^1;
sbit S_M  = P2^2;               /* 中间 */
sbit S_R1 = P2^3;
sbit S_R2 = P2^4;               /* 最右 */

sbit LED_MODE = P2^5;           /* 模式指示灯（可选） */

/* 2 个按键接在 2 个外部中断脚上 */
sbit KEY_SEL = P3^2;            /* INT0：选择键 */
sbit KEY_OK  = P3^3;            /* INT1：确认键 */

/*------------------------------ 可调参数 ------------------------------*/
#define FOSC        11059200UL  /* 晶振频率：用蓝牙 9600 建议 11.0592MHz */
#define T0_1MS      (FOSC / 12 / 1000)   /* 1ms 需要多少个机器周期(921) */
#define PWM_DIV     10          /* 软件 PWM 分度数：10 分度 × 1ms = 100Hz */
#define SPEED_MAX   10          /* 速度上限，正好等于 PWM 分度数(0~10) */
#define LINE_SPEED  6           /* 巡线模式的基础速度 0~10 */
#define LINE_BLACK  0           /* 传感器压黑线时输出 0；若你的模块相反改成 1 */
#define FRAME_HEAD  0xAA        /* 蓝牙数据帧头 */

/* 电机方向码 */
#define DIR_STOP    0           /* 停止：两个方向脚都低，电机断电滑行 */
#define DIR_FWD     1           /* 正转（前进） */
#define DIR_BACK    2           /* 反转（后退） */

uint8_t base_timer0;            /*基础时间，实时系统基础*/
uint8_t sum_timer1;             /* 计时器的剩余时间（ms），get_sum_timer1() 用 */
uint8_t key1_flag,key2_flag;    /* 两个按键的中断标志 */
uint8_t mode_flag=0;            /*模式标志位，0为蓝牙模式，1为巡线模式*/
typedef struct speed_t{
    uint8_t left;
    uint8_t right;
}speed_t;
uint8_t redata[4];              /*蓝牙接收数据缓存*/

speed_t speed_cur;              /* 当前目标速度（0~10），中断里做 PWM 输出用 */
uint8_t motor_dir_l = DIR_STOP; /* 左电机方向 */
uint8_t motor_dir_r = DIR_STOP; /* 右电机方向 */
uint8_t mode_sel = 0;           /* 选择键选中的模式，等确认键生效 */
uint8_t ms_tick = 0;            /* 毫秒节拍，Timer0 中断里加 1 */
static uint8_t t0_h, t0_l;      /* Timer0 的重装值 */

/* 函数声明（C51 里被调用的函数必须先声明） */
void pwm_init(speed_t *speed, uint8_t pwm_num);
void set_motion(uint8_t ldir, uint8_t rdir, uint8_t ls, uint8_t rs);
void car_stop(void);
uint16_t get_sum_timer1(unsigned int ticks);
void key_scan(void);
void line_scan(void);

//设置一个系统软件延时
//ticks：延时的毫秒数（12MHz 晶振下，与 main.c 里的 Delay1ms 完全一样的循环）
//返回 1 表示延时完成
uint8_t systim_delay(unsigned int ticks){
    unsigned char i, j;

    while(ticks != 0){
        i = 2;
        j = 239;
        do{
            while(--j);
        }while(--i);
        ticks--;
    }
    return 1;
}

//一个基准tim定时
//Timer0 方式1，每 ticks 个机器周期进一次中断，ticks 传 T0_1MS 就是 1ms
//基准定时
uint8_t gettimer0_init(unsigned int ticks){
    uint16_t reload;

    //基准定时
    reload = (uint16_t)(65536UL - (uint16_t)ticks);
    t0_h = (uint8_t)(reload >> 8);              /* 重装值高 8 位 */
    t0_l = (uint8_t)(reload & 0x00FF);          /* 重装值低 8 位 */

    TMOD = (uint8_t)((TMOD & 0xF0) | 0x01);     /* Timer0：方式1，16 位定时 */
    TH0  = t0_h;
    TL0  = t0_l;
    base_timer0 = 0;                            /* 分度计数清零 */
    TF0  = 0;
    ET0  = 1;                                   /* 允许 Timer0 中断 */
    TR0  = 1;                                   /* 启动 Timer0 */

    //循环
    /* “循环”就是软件 PWM 的 10 个分度循环：Timer0 每进一次中断走一格 0~9，
       走满 PWM_DIV 格就是一个 PWM 周期。这里返回起始分度 0。 */
    return (uint8_t)(base_timer0 % PWM_DIV);
}

//初始化一个计时器
//ticks != 0：重新装载计时长度（ms，最大 255），并从当前时刻开始计时，返回 ticks
//ticks == 0：返回剩余时间（ms），返回 0 表示计时时间到
//说明：AT89C52 的 Timer0 在做 PWM 和毫秒基准、Timer1 已给串口做波特率了，
//      Timer2 本程序不用，所以这里用 Timer0 的 1ms 节拍(ms_tick)做扣减计时，
//      函数名和接口保持不变
uint16_t get_sum_timer1(unsigned int ticks){
    static uint8_t last_ms = 0;     /* 上次取计时值时的毫秒节拍 */
    uint8_t now, diff;

    if(ticks != 0){
        /* 初始化（重装）计时器 */
        sum_timer1 = (ticks > 255) ? 255 : (uint8_t)ticks;
        last_ms = ms_tick;                          /* 记下计时起点 */
        return (uint16_t)ticks;
    }

    /* 查询：把上一次到现在过去的毫秒数扣掉 */
    now  = ms_tick;
    diff = (uint8_t)(now - last_ms);                /* 8 位自动回绕 */
    last_ms = now;

    if(diff >= sum_timer1){
        sum_timer1 = 0;                             /* 时间到 */
    }else{
        sum_timer1 = (uint8_t)(sum_timer1 - diff);
    }
    return (uint16_t)sum_timer1;
}

//初始化串口作为蓝牙接收器，占用一个内部中断
void sreceiver_init(){
    TMOD = (uint8_t)((TMOD & 0x0F) | 0x20); /* Timer1：方式2，8 位自动重装，作波特率发生器 */
    SCON = 0x50;                            /* 串口方式1：8 位数据，允许接收 REN=1 */
    PCON = 0x00;                            /* SMOD=0，波特率不加倍 */
    TH1  = 0xFD;                            /* 11.0592MHz 晶振：9600bps；
                                               若用 12MHz 晶振，9600 误差太大，改成
                                               PCON=0x80 + TH1=0xF3 才是 4800bps */
    TL1  = 0xFD;
    TR1  = 1;                               /* 启动波特率发生器 */

    /* 串口本身占用内部中断 4。本程序用 receiver_data() 查询 RI 标志收数据，
       所以 ES 先不开；如果要改成中断接收，把 ES 置 1，再补一个
       void uart_isr(void) interrupt 4 把 SBUF 存进 redata[] 即可。 */
    ES   = 0;
    RI   = 0;
    TI   = 0;
}

//蓝牙接收一帧数据：帧头 0xAA + 方向 + 左轮速度 + 右轮速度
//返回 1：收到并处理完一帧；返回 0：没数据 / 超时 / 帧头或命令不对
uint8_t receiver_data(){
    uint8_t i;

    get_sum_timer1(20);                 /* 本帧最多等 20ms，等不到就放弃，不卡住主循环 */

    //帧头
    while(RI==0){                       /* 等第一个字节 */
        if(get_sum_timer1(0) == 0){
            return 0;                   /* 超时 */
        }
    }
    redata[0] = SBUF;                   /* 读走数据会自动清 RI，这里再清一次更保险 */
    RI = 0;
    if(redata[0] != FRAME_HEAD){
        return 0;                       /* 帧头不对，丢掉 */
    }

    /* 接着收后面的 3 个字节 */
    for(i = 1; i < 4; i++){
        while(RI==0){
            if(get_sum_timer1(0) == 0){
                return 0;               /* 超时 */
            }
        }
        redata[i] = SBUF;
        RI = 0;
    }

    //修改speed_t
    switch(redata[1]){
        case 0x00:                                      /* 停止 */
            car_stop();
            break;
        case 0x01:                                      /* 前进 */
            set_motion(DIR_FWD,  DIR_FWD,  redata[2], redata[3]);
            break;
        case 0x02:                                      /* 后退 */
            set_motion(DIR_BACK, DIR_BACK, redata[2], redata[3]);
            break;
        case 0x03:                                      /* 原地左转：左轮倒转，右轮正转 */
            set_motion(DIR_BACK, DIR_FWD,  redata[2], redata[3]);
            break;
        case 0x04:                                      /* 原地右转：左轮正转，右轮倒转 */
            set_motion(DIR_FWD,  DIR_BACK, redata[2], redata[3]);
            break;
        default:
            return 0;                                   /* 命令不认识，保持原来的动作 */
    }
    return 1;
}

//2个pwm输出，4个gpio通用输出用于控制正反转
//speed：目标速度（0~10）
//pwm_num：Timer0 中断给出的当前分度（0~9），分度小于速度就输出高电平
void pwm_init(speed_t *speed,uint8_t pwm_num){
    /* 前后判断：先按方向码摆好 4 个方向脚，再让 PWM 脚决定这一格通不通电 */
    switch(motor_dir_l){
        case DIR_FWD:  M_L_IN1 = 1; M_L_IN2 = 0; break;   /* 正转 */
        case DIR_BACK: M_L_IN1 = 0; M_L_IN2 = 1; break;   /* 反转 */
        default:       M_L_IN1 = 0; M_L_IN2 = 0; break;   /* 停止：断电滑行 */
    }
    switch(motor_dir_r){
        case DIR_FWD:  M_R_IN1 = 1; M_R_IN2 = 0; break;
        case DIR_BACK: M_R_IN1 = 0; M_R_IN2 = 1; break;
        default:       M_R_IN1 = 0; M_R_IN2 = 0; break;
    }

    /* pwm 输出逻辑：分度从 0 走到 9，速度 10 就是 10 格全通，占空比 100% */
    if(pwm_num<speed->left){
        M_L_PWM = 1;    /* 转 */
    }else{
        M_L_PWM = 0;    /* 不转 */
    }
    if(pwm_num<speed->right){
        M_R_PWM = 1;    /* 转 */
    }else{
        M_R_PWM = 0;    /* 不转 */
    }
}

/* 设置小车运动状态：方向码 0/1/2，速度 0~10（超过上限自动限幅） */
void set_motion(uint8_t ldir, uint8_t rdir, uint8_t ls, uint8_t rs){
    motor_dir_l = ldir;
    motor_dir_r = rdir;
    speed_cur.left  = (ls > SPEED_MAX) ? SPEED_MAX : ls;
    speed_cur.right = (rs > SPEED_MAX) ? SPEED_MAX : rs;
}

/* 停车：方向脚全低 + 速度清零 */
void car_stop(void){
    set_motion(DIR_STOP, DIR_STOP, 0, 0);
}

/* Timer0 中断：1ms 基准节拍，同时做两件事
 *   1) 10 分度软件 PWM：每次中断走一格，一格 1ms，一个周期 10ms = 100Hz
 *   2) 毫秒节拍 ms_tick++，给 get_sum_timer1() 计时用
 */
void timer0_isr(void) interrupt 1{
    TH0 = t0_h;                     /* 重装初值 */
    TL0 = t0_l;

    base_timer0++;
    if(base_timer0 >= PWM_DIV){
        base_timer0 = 0;            /* 分度循环：0,1,2,...,9,0,... */
    }

    pwm_init(&speed_cur, base_timer0);  /* pwm 输出逻辑：每个分度刷新一次输出 */
    ms_tick++;                      /* 毫秒节拍，8 位自动回绕 */
}

/* 外部中断 0：选择键，只置标志，消抖和动作放到 key_scan() 里做 */
void int0_isr(void) interrupt 0{
    key1_flag = 1;
    EX0 = 0;                        /* 先关掉本中断，防止按键抖动进很多次 */
}

/* 外部中断 1：确认键 */
void int1_isr(void) interrupt 2{
    key2_flag = 1;
    EX1 = 0;
}

//2个按键占用2个外部中断，一个选择键，一个确认键（蓝牙模式和巡线模式）
//选择键：在“蓝牙模式 / 巡线模式”之间挑一个（只改 mode_sel，还不生效）
//确认键：把挑中的模式真正切过去，同时先停车
void key_scan(){
    if(key1_flag){
        systim_delay(10);           /* 软件消抖 10ms */
        if(KEY_SEL == 0){           /* 低电平确认真的按下了 */
            mode_sel = (mode_sel == 0) ? 1 : 0;     /* 0 蓝牙 <-> 1 巡线 */
        }
        key1_flag = 0;
        EX0 = 1;                    /* 处理完了，重新允许外部中断 0 */
    }

    if(key2_flag){
        systim_delay(10);
        if(KEY_OK == 0){
            if(mode_sel != mode_flag){
                mode_flag = mode_sel;               /* 模式生效 */
                car_stop();                         /* 切模式先停车，安全 */
                LED_MODE = (mode_flag == 0) ? 1 : 0;/* 灭=蓝牙模式 亮=巡线模式 */
            }
        }
        key2_flag = 0;
        EX1 = 1;
    }
}

//巡线模式逻辑判断,5个红外传感器，5个GPIO输入
//传感器从左到右：P2.0 P2.1 P2.2 P2.3 P2.4，压黑线那一路为 1（见 LINE_BLACK）
//判断顺序：先看最外侧两路（大角度急转），再看次外侧（微调），最后中间（直行）
void line_scan(){
    uint8_t s;

#if (LINE_BLACK == 0)
    s = (uint8_t)(~P2 & 0x1F);      /* 模块压黑线输出 0，取反后 1 = 压线 */
#else
    s = (uint8_t)(P2 & 0x1F);       /* 模块压黑线输出 1，直接用 */
#endif

    if(s == 0x00){
        /* 五路都没压到线：丢线。保持上一次的方向和速度继续走，
           比直接停车更容易找回线；想更稳可以让它原地慢慢转。 */
        return;
    }

    if(s & 0x01){                   /* 最左压线：线在左边，原地左转 */
        set_motion(DIR_BACK, DIR_FWD, LINE_SPEED, LINE_SPEED);
    }else if(s & 0x10){             /* 最右压线：线在右边，原地右转 */
        set_motion(DIR_FWD, DIR_BACK, LINE_SPEED, LINE_SPEED);
    }else if(s & 0x02){             /* 左二压线：有点偏左，左轮减速 */
        set_motion(DIR_FWD, DIR_FWD, (uint8_t)(LINE_SPEED > 4 ? LINE_SPEED - 4 : 0), LINE_SPEED);
    }else if(s & 0x08){             /* 右二压线：有点偏右，右轮减速 */
        set_motion(DIR_FWD, DIR_FWD, LINE_SPEED, (uint8_t)(LINE_SPEED > 4 ? LINE_SPEED - 4 : 0));
    }else{                          /* 中间压线，或十字横线全压：直行 */
        set_motion(DIR_FWD, DIR_FWD, LINE_SPEED, LINE_SPEED);
    }
}

void main(){
    //初始化
    M_L_IN1 = 0; M_L_IN2 = 0;       /* 上电先把电机方向脚拉低 */
    M_R_IN1 = 0; M_R_IN2 = 0;
    M_L_PWM = 0; M_R_PWM = 0;
    P2 = 0x3F;                      /* 传感器脚作输入，指示灯先关 */

    car_stop();                     /* 速度清零 */
    sreceiver_init();               /* 串口：蓝牙接收（Timer1 做波特率） */
    gettimer0_init(T0_1MS);         /* Timer0：1ms 基准定时 + 软件 PWM */
    get_sum_timer1(0);              /* 计时器复位 */

    IT0 = 1;                        /* 外部中断 0：下降沿触发（选择键） */
    IT1 = 1;                        /* 外部中断 1：下降沿触发（确认键） */
    EX0 = 1;
    EX1 = 1;
    key1_flag = 0;
    key2_flag = 0;

    mode_flag = 0;                  /* 默认蓝牙模式 */
    mode_sel  = 0;
    LED_MODE  = 1;                  /* 指示灯灭（低电平点亮） */

    EA = 1;                         /* 最后再开总中断 */

    while(1){
        //按键扫描
        key_scan();

        if(mode_flag == 0){
            /* 蓝牙模式：查询串口，收到一帧就修改 speed_t / 方向 */
            receiver_data();
        }else{
            /* 巡线模式：5 路红外判断后修改 speed_t / 方向 */
            line_scan();
        }
    }
}