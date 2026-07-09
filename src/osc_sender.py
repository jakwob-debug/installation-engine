from pythonosc.udp_client import SimpleUDPClient


class OSCSender:
    def __init__(self, ip="127.0.0.1", port=8000):
        self.client = SimpleUDPClient(ip, port)

    def send_pillar(self, presence, distance, activity):
        self.client.send_message("/pillar/1/presence", float(presence))
        self.client.send_message("/pillar/1/distance", float(distance))
        self.client.send_message("/pillar/1/activity", float(activity))