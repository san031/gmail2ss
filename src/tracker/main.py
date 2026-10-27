import sys
print(sys.path[0])

from sheet import add_application, schedule_interview

print(add_application("Acme", "Data Engineer", email_id="msg-001")["action"])
print(schedule_interview("Acme", "Data Engineer", "2026-11-02", email_id="msg-002")["action"])
print(schedule_interview("Acme", "Data Engineer", "2026-11-02", email_id="msg-002")["action"])
