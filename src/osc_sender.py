from pythonosc.udp_client import SimpleUDPClient

from src.config import PILLAR_ID, OSC_IP, OSC_PORT


class OSCSender:
    def __init__(self):
        self.client = SimpleUDPClient(OSC_IP, OSC_PORT)

    def send_pillar(self, presence, distance, activity):
        self.client.send_message(f"/pillar/{PILLAR_ID}/presence", float(presence))
        self.client.send_message(f"/pillar/{PILLAR_ID}/distance", float(distance))
        self.client.send_message(f"/pillar/{PILLAR_ID}/activity", float(activity))
        