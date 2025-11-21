const float Vref = 3.3;
const int ADCbits = 16;
const int det1 = A0;
const int det2 = A1;

void setup() {
  Serial.begin(1000000);
  analogReadResolution(ADCbits);
  Serial.println("H,V");
  delay(100);
}

void loop() {
  const int N = 50;
  long sum1 = 0;
  long sum2 = 0;
  for (int i = 0; i < N; i++) {
    sum1 += analogRead(det1);
    sum2 += analogRead(det2);
    //delay(2);
  }
  float adcRaw1 = (float)sum1 / N;
  float adcRaw2 = (float)sum2 / N;
  float V1 = (adcRaw1 / ((1 << ADCbits) - 1)) * Vref;
  float V2 = (adcRaw2 / ((1 << ADCbits) - 1)) * Vref;

  float H = V1 ;
  float V = V2 ;
  

  // Exibe os dados em formato correto
  
  Serial.print(H, 6); Serial.print(", "); Serial.println(V, 6); 
  
  delayMicroseconds(50);
}
