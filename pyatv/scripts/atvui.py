import argparse
import asyncio
import sys
import tkinter as tk
from asyncio import Lock

import pyatv
from pyatv import Protocol
from pyatv.interface import AppleTV

CANVAS_WIDTH = 600
CANVAS_HEIGHT = 600
PAD_WIDTH = 1000
PAD_HEIGHT = 1000

class AtvUi(tk.Frame):
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.canvas = tk.Canvas(self, width=CANVAS_WIDTH, height=CANVAS_HEIGHT)
        self.canvas.pack(side="top", fill="both", expand=True)
        self.text_id = self.canvas.create_text(10, 10, anchor="nw", text="Virtual pad : drag the pointer")
        root.bind('<ButtonPress-1>', self.click)
        root.bind('<ButtonRelease-1>', self.release)
        self.atv: AppleTV | None = None
        self.loop = asyncio.get_event_loop()
        self.lock = Lock()
        self.x = -1
        self.y = -1
        self.touch_reset = False

    async def atvconnect(self, loop, ip_address: str, credentials: str) -> AppleTV | None:
        print("Discovering devices on network...")
        self.loop = loop
        atvs = await pyatv.scan(loop)
        if not atvs:
            print("No device found", file=sys.stderr)
            return None

        config = None
        for atv in atvs:
            print(str(atv.address) + " " + atv.name)
            if str(atv.address) == ip_address:
                config = atv
                break
        config.set_credentials(Protocol.Companion, credentials)
        print(f"Connecting to {config.address}")
        atv = await pyatv.connect(config, loop)
        self.atv = atv
        return atv

    async def send_event(self, x: int, y: int, mode: int):
        if self.lock.locked():
            return
        await self.lock.acquire()
        # print("%r, %r" % (x, y))
        await self.atv.touchgestures.touch_event(x, y, mode)
        await asyncio.sleep(0.001)
        self.lock.release()

    def getX(self, x) -> int:
        return min(max(int(x * PAD_WIDTH / CANVAS_WIDTH), 0), PAD_WIDTH)

    def getY(self, y) -> int:
        return min(max(int(y * PAD_HEIGHT / CANVAS_HEIGHT), 0), PAD_HEIGHT)

    def click(self, event):
        self.canvas.itemconfig(self.text_id, text="Click")
        self.x = self.getX(event.x)
        self.y = self.getY(event.y)
        # asyncio.run(self.atv.touchgestures.touch_gesture(100,400, 300,410,1000))
        self.loop.run_until_complete(self.send_event(self.x, self.y, 1))
        print("%r, %r : %r" % (self.x, self.y, 1))
        root.bind('<B1-Motion>', self.motion)

    def release(self, event):
        self.canvas.itemconfig(self.text_id, text="Release")
        self.loop.run_until_complete(self.atv.touchgestures.touch_event(self.getX(event.x), self.getY(event.y), 4))
        print("%r, %r : %r" % (self.getX(event.x), self.getY(event.y), 4))
        root.unbind('<B1-Motion>')

    def motion(self, event):
        x, y = event.x, event.y
        self.canvas.itemconfig(self.text_id, text='{}, {}'.format(x, y))
        target_x = self.getX(event.x)
        target_y = self.getY(event.y)
        if ((self.x != target_x and target_x in [0, PAD_WIDTH])
                or (self.y != target_y and target_y in [0, PAD_HEIGHT])):
            self.touch_reset = True
            self.loop.run_until_complete(self.atv.touchgestures.touch_event(target_x, target_y, 4))
        elif self.x != target_x or self.y != target_y:
            if self.touch_reset:
                self.loop.run_until_complete(self.atv.touchgestures.touch_event(target_x, target_y, 1))
                self.touch_reset = False
            else:
                self.loop.run_until_complete(self.send_event(target_x, target_y, 3))
        self.x = target_x
        self.y = target_y


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", help="Apple TV IP address", required=True)
    parser.add_argument("--credentials", help="Companion credentials", required=True)
    args = parser.parse_args()
    if not args.ip or not args.credentials:
        parser.error("Missing arguments")
        exit(1)

    ip_address = args.ip
    credentials = args.credentials

    loop = asyncio.get_event_loop() or asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    root = tk.Tk()
    root.title("Apple TV UI")
    view = AtvUi(root)
    view.pack(side="top", fill="both", expand=True)
    loop.run_until_complete(view.atvconnect(loop, ip_address, credentials))
    root.mainloop()
    print("Exit")
    view.atv.close()
