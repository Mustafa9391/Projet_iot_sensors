/*

Copyright (c) 2012-2014 RedBearLab

Permission is hereby granted, free of charge, to any person obtaining a copy of this software 
and associated documentation files (the "Software"), to deal in the Software without restriction, 
including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, 
subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR 
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE 
FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, 
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

*/

#include "mbed.h"
#include "ble/BLE.h"
#include "Servo.h"


#define BLE_UUID_TXRX_SERVICE            0x0000 /**< The UUID of the Nordic UART Service. */
#define BLE_UUID_TX_CHARACTERISTIC       0x0002 /**< The UUID of the TX Characteristic. */
#define BLE_UUIDS_RX_CHARACTERISTIC      0x0003 /**< The UUID of the RX Characteristic. */

#define TXRX_BUF_LEN                     20

#define DIGITAL_OUT_PIN                  P0_9       //TXD
#define DIGITAL_IN_PIN                   P0_10      //CTS
#define PWM_PIN                          P0_11      //RXD
#define SERVO_PIN                        P0_8       //RTS
#define ANALOG_IN_PIN                    P0_4       //P04
#include <stdio.h>
#include "mbed.h"
#include "BMP180.h"

I2C i2c(p29, p28);
BMP180 bmp180(&i2c);
float pressureRef = 101580;


float temperature;
int pressure;
float altitude;

BLE             ble;

DigitalOut      LED_SET(DIGITAL_OUT_PIN);
DigitalIn       BUTTON(DIGITAL_IN_PIN);
PwmOut          PWM(PWM_PIN);
AnalogIn        ANALOG(ANALOG_IN_PIN);
Servo           MYSERVO(SERVO_PIN);

//Serial pc(USBTX, USBRX);

static uint8_t analog_enabled = 0;
static uint8_t pressure_enabled=0;
static uint8_t old_state = 0;

// The Nordic UART Service
static const uint8_t uart_base_uuid[] = {0x71, 0x3D, 0, 0, 0x50, 0x3E, 0x4C, 0x75, 0xBA, 0x94, 0x31, 0x48, 0xF1, 0x8D, 0x94, 0x1E};
static const uint8_t uart_tx_uuid[]   = {0x71, 0x3D, 0, 3, 0x50, 0x3E, 0x4C, 0x75, 0xBA, 0x94, 0x31, 0x48, 0xF1, 0x8D, 0x94, 0x1E};
static const uint8_t uart_rx_uuid[]   = {0x71, 0x3D, 0, 2, 0x50, 0x3E, 0x4C, 0x75, 0xBA, 0x94, 0x31, 0x48, 0xF1, 0x8D, 0x94, 0x1E};
static const uint8_t uart_base_uuid_rev[] = {0x1E, 0x94, 0x8D, 0xF1, 0x48, 0x31, 0x94, 0xBA, 0x75, 0x4C, 0x3E, 0x50, 0, 0, 0x3D, 0x71};


uint8_t txPayload[TXRX_BUF_LEN] = {0,};
uint8_t rxPayload[TXRX_BUF_LEN] = {0,};

//static uint8_t rx_buf[TXRX_BUF_LEN];
//static uint8_t rx_len=0;


GattCharacteristic  txCharacteristic (uart_tx_uuid, txPayload, 1, TXRX_BUF_LEN, GattCharacteristic::BLE_GATT_CHAR_PROPERTIES_WRITE | GattCharacteristic::BLE_GATT_CHAR_PROPERTIES_WRITE_WITHOUT_RESPONSE);
                                      
GattCharacteristic  rxCharacteristic (uart_rx_uuid, rxPayload, 1, TXRX_BUF_LEN, GattCharacteristic::BLE_GATT_CHAR_PROPERTIES_NOTIFY);
                                      
GattCharacteristic *uartChars[] = {&txCharacteristic, &rxCharacteristic};

GattService         uartService(uart_base_uuid, uartChars, sizeof(uartChars) / sizeof(GattCharacteristic *));



void disconnectionCallback(const Gap::DisconnectionCallbackParams_t *params)
{
    //pc.printf("Disconnected \r\n");
    //pc.printf("Restart advertising \r\n");
    ble.gap().startAdvertising();
}

void WrittenHandler(const GattWriteCallbackParams *Handler)
{   
    uint8_t buf[TXRX_BUF_LEN];
    uint16_t bytesRead;
    
    if (Handler->handle == txCharacteristic.getValueAttribute().getHandle()) 
    {
        ble.readCharacteristicValue(txCharacteristic.getValueAttribute().getHandle(), buf, &bytesRead);
        memset(txPayload, 0, TXRX_BUF_LEN);
        memcpy(txPayload, buf, TXRX_BUF_LEN);       
        
        //for(index=0; index<bytesRead; index++)
            //pc.putc(buf[index]);
            
        if(buf[0] == 0x01)
        {
            if(buf[1] == 0x01)
                LED_SET = 1;
            else
                LED_SET = 0;    
        }
        else if(buf[0] == 0xA0)
        {
            if(buf[1] == 0x01){
                analog_enabled = 1;
                pressure_enabled=0;}
            else{
                pressure_enabled=1;
                analog_enabled = 0;}
        }
        else if(buf[0] == 0x02)
        {
            float value = (float)buf[1]/255;
            PWM = value;
        }
        else if(buf[0] == 0x03)
        {
            MYSERVO.write(buf[1]);
        }
        else if(buf[0] == 0x04)
        {
            analog_enabled = 0;
            PWM = 0;
            MYSERVO.write(0);
            LED_SET = 0;
            old_state = 0;    
        }

    }
}
/*
void uartCB(void)
{   
    while(pc.readable())    
    {
        rx_buf[rx_len++] = pc.getc();    
        if(rx_len>=20 || rx_buf[rx_len-1]=='\0' || rx_buf[rx_len-1]=='\n')
        {
            ble.updateCharacteristicValue(rxCharacteristic.getValueAttribute().getHandle(), rx_buf, rx_len); 
            pc.printf("RecHandler \r\n");
            pc.printf("Length: ");
            pc.putc(rx_len);
            pc.printf("\r\n");
            rx_len = 0;
            break;
        }
    }
}
*/
void m_status_check_handle(void)
{   
    uint8_t buf[4];
    if (analog_enabled)  // if analog reading enabled
    {
        // Read and send out
        uint16_t  value =(unsigned int) temperature; 
        buf[0] = (0x0B);
        buf[1] = (value >> 8);
        buf[2] = (value);
        ble.updateCharacteristicValue(rxCharacteristic.getValueAttribute().getHandle(), buf, 3); 
    }
    if (pressure_enabled){
        uint32_t value=pressure;
        buf[0] = (value>>24);
        buf[1] = (value >> 16);
        buf[2] = (value >>8);
        buf[3] =(value);
        ble.updateCharacteristicValue(rxCharacteristic.getValueAttribute().getHandle(), buf, 4);
        }
    
    // If digital in changes, report the state
    if (BUTTON != old_state)
    {
        old_state = BUTTON;
        
        if (BUTTON == 1)
        {
            buf[0] = (0x0A);
            buf[1] = (0x01);
            buf[2] = (0x00);    
            ble.updateCharacteristicValue(rxCharacteristic.getValueAttribute().getHandle(), buf, 3); 
        }
        else
        {
            buf[0] = (0x0A);
            buf[1] = (0x00);
            buf[2] = (0x00);
           ble.updateCharacteristicValue(rxCharacteristic.getValueAttribute().getHandle(), buf, 3); 
        }
    }
}


int main(void)
{   //Init sensor 
    if (bmp180.init() != 0) {
            printf("Error communicating with BMP180\n");
        } else {
            printf("Initialized BMP180\n");
    }
    wait(1);
    
    Ticker ticker;
    ticker.attach_us(m_status_check_handle, 200000);
    
    ble.init();
    ble.onDisconnection(disconnectionCallback);
    ble.onDataWritten(WrittenHandler);  
    
    //pc.baud(9600);
    //pc.printf("SimpleChat Init \r\n");

    //pc.attach( uartCB , pc.RxIrq);
    
    // setup advertising 
    ble.accumulateAdvertisingPayload(GapAdvertisingData::BREDR_NOT_SUPPORTED);
    ble.setAdvertisingType(GapAdvertisingParams::ADV_CONNECTABLE_UNDIRECTED);
    ble.accumulateAdvertisingPayload(GapAdvertisingData::SHORTENED_LOCAL_NAME,
                                    (const uint8_t *)"Biscuit", sizeof("Biscuit") - 1);
    ble.accumulateAdvertisingPayload(GapAdvertisingData::COMPLETE_LIST_128BIT_SERVICE_IDS,
                                    (const uint8_t *)uart_base_uuid_rev, sizeof(uart_base_uuid));
    // 100ms; in multiples of 0.625ms. 
    ble.setAdvertisingInterval(160);

    ble.addService(uartService);
    
    ble.startAdvertising(); 
    
    //pc.printf("Advertising Start \r\n");
    
    while(1)
    {
        bmp180.startTemperature();
        wait_ms(5);     // Wait for conversion to complete
        if(bmp180.getTemperature(&temperature) != 0) {
            printf("Error getting temperature\n");
            continue;
        }

        bmp180.startPressure(BMP180::ULTRA_LOW_POWER);
        wait_ms(10);    // Wait for conversion to complete
        if(bmp180.getPressure(&pressure) != 0) {
            printf("Error getting pressure\n");
            continue;
        }
        altitude = bmp180.calcAltitude((float) pressure);
        printf("Pressure = %d Pa Temperature = %f C\ Altitude = %f \n", pressure, temperature, altitude);
        
        wait(1);
        
        ble.waitForEvent(); 
    }

}































