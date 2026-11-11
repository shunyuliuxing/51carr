//个人程序设计
#include <REGX52.H>

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
uint8_t redata[4];//蓝牙接收数据缓存

//设置一个系统软件延时
uint8_t systim_delay(unsigned int ticks){

}
//一个基准tim定时
uint8_t gettimer0_init(unsigned int ticks){
//基准定时
//循环

}
//初始化一个计时器
uint16_t get_sum_timer1(unsigned int ticks){ 
}
//初始化串口作为蓝牙接收器，占用一个内部中断
void sreceiver_init(){

}
uint8_t receiver_data(){
while(RI==0){
    //帧头
    //修改speed_t 
}
}
//2个pwm输出，4个gpio通用输出用于控制正反转
void pwm_init(speed_t *speed,uint8_t pwm_num){
    pwm_num = gettimer0_init(unsigned int ticks)%10;
    //前后判断

    //pwm 输出逻辑
    if(pwm_num<speed->left){
        //转
    }else{
        //不转
    }
    if(pwm_num<speed->right){
        //转
    }else{
        //不转
    }
}


//2个按键占用2个外部中断，一个选择键，一个确认键（蓝牙模式和巡线模式）
key_scan(){

}
//巡线模式逻辑判断,5个红外传感器，5个GPIO输入
line_scan(){

}
void main(){ 
    //初始化

    while(1){
        //按键扫描
        key_scan();


    }
}

void timer0() interrupt 1{
    //基础时间计数
    base_timer0++;
    //pwm输出
    pwm_init(speed_t *speed,uint8_t pwm_num);
}

void timer1() interrupt 2{

}


void Delay1ms(unsigned int xms)		//@12.000MHz
{
	unsigned char i, j;
	while(xms)
	{
		i = 2;
		j = 239;
		do
		{
			while (--j);
		} while (--i);
		xms--;
	}
}
