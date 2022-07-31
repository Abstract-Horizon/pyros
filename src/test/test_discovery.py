

from discovery import Discovery


discovery = Discovery("TEST")

test_ips = ["192.168.1.2", "172.24.1.5", "55.55.55.55"]
for test_ip in test_ips:
    found_id = discovery._get_ip_address(test_ip)
    print(f"For {test_ip} we got {found_id}")
