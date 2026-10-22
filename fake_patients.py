"""5 SYNTHETIC patients (all names/numbers are invented). Used to test extraction + PII masking.
`expect` holds the gold values for quick checks."""
import json
PATIENTS = [
 {"id": "P001", "name": "Rakesh Kumar Sahoo", "phone": "9876501234", "aadhaar": "2345 6789 0123", "lang": "en",
  "text": "My name is Rakesh Kumar Sahoo, phone 9876501234. I have had high fever for 3 days with severe headache and vomiting. "
          "Temperature 102 F, SpO2 93, pulse 104. I have diabetes. Taking paracetamol. No allergies.",
  "expect": {"duration": "3 days", "severity": "severe", "spo2": 93, "temp_c": 38.9, "pulse": 104}},
 {"id": "P002", "name": "Sunita Devi", "phone": "9123456780", "aadhaar": "4567 1234 8890", "lang": "hi",
  "text": "मेरा नाम सुनीता देवी है, फोन 9123456780। मैं 7 महीने गर्भवती हूँ। 2 दिन से बहुत तेज सिरदर्द है और धुंधला दिखाई दे रहा है। बीपी 150/100।",
  "expect": {"duration": "2 days", "severity": "severe", "bp_sys": 150, "bp_dia": 100, "preg": "pregnant, 7 months"}},
 {"id": "P003", "name": "Mohammad Imran", "phone": "8800123456", "aadhaar": "7890 4567 1122", "lang": "hinglish",
  "text": "Mera naam Imran hai. Seene mein dard hai aur saans phoolna 2 ghante se, achanak shuru hua. Pulse 118, oxygen 89.",
  "expect": {"duration": "2 hours", "onset": "sudden", "spo2": 89, "pulse": 118}},
 {"id": "P004", "name": "Priya Nayak", "phone": "7008765432", "aadhaar": "1234 5678 9012", "lang": "en",
  "text": "Hostel student Priya Nayak, contact 7008765432. Mild cough and body ache since 1 day. Temperature 99.5 F. No other problems. Allergic to penicillin.",
  "expect": {"duration": "1 day", "severity": "mild", "temp_c": 37.5}},
 {"id": "P005", "name": "Baby of Lakshmi Behera", "phone": "9437011223", "aadhaar": "5566 7788 9900", "lang": "hinglish",
  "text": "Mere bacche ko kal se bukhar hai aur jhatke aa rahe hain, doodh nahi pi raha. 1 din se hai. Temperature 103 F.",
  "expect": {"duration": "1 days", "temp_c": 39.4}},
]
if __name__ == "__main__":
    json.dump(PATIENTS, open("fake_patients.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("wrote fake_patients.json")
