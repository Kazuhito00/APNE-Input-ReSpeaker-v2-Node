#!/usr/bin/env python
# -*- coding: utf-8 -*-
import struct
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import dearpygui.dearpygui as dpg  # type: ignore
import numpy as np
import usb.core
import usb.util
from node_editor.util import dpg_set_value, get_tag_name_list  # type: ignore

from node.node_abc import DpgNodeABC  # type: ignore


# ReSpeaker parameter definitions
PARAMETERS = {
    'VOICEACTIVITY': (19, 32, 'int', 1, 0, 'ro', 'VAD voice activity status.', '0 = false (no voice activity)', '1 = true (voice activity)'),
}


class Tuning:
    TIMEOUT = 100000

    def __init__(self, dev):
        self.dev = dev

    def read(self, name):
        try:
            data = PARAMETERS[name]
        except KeyError:
            return

        id = data[0]

        cmd = 0x80 | data[1]
        if data[2] == 'int':
            cmd |= 0x40

        length = 8

        response = self.dev.ctrl_transfer(
            usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR | usb.util.CTRL_RECIPIENT_DEVICE,
            0, cmd, id, length, self.TIMEOUT)

        response = struct.unpack(b'ii', response.tobytes())

        if data[2] == 'int':
            result = response[0]
        else:
            result = response[0] * (2.**response[1])

        return result

    def is_voice(self):
        return self.read('VOICEACTIVITY')

    def close(self):
        usb.util.dispose_resources(self.dev)


class Node(DpgNodeABC):
    _ver: str = "0.0.1"

    node_label: str = "ReSpeaker v2 VAD"
    node_tag: str = "ReSpeakerV2VAD"

    def __init__(self) -> None:
        self._node_data = {}
        self._add_node_flag = False  # 単一ノード制御フラグ

        # USB経由でReSpeakerデバイスを取得（VAD用）
        self._respeaker_device = None
        try:
            dev = usb.core.find(idVendor=0x2886, idProduct=0x0018)
            if dev:
                self._respeaker_device = Tuning(dev)
        except Exception as e:
            print(f"Failed to initialize ReSpeaker USB device: {e}")
            self._respeaker_device = None

    def add_node(
        self,
        parent: str,
        node_id: int,
        pos: List[int] = [0, 0],
        setting_dict: Optional[Dict[str, Any]] = None,
        callback: Optional[Any] = None,
    ) -> Optional[str]:
        if self._add_node_flag:
            return None
        self._add_node_flag = True
        # タグ名
        tag_name_list: List[Any] = get_tag_name_list(
            node_id,
            self.node_tag,
            [],
            [
                self.TYPE_INT,
                self.TYPE_TIME_MS,
            ],
        )
        tag_node_name: str = tag_name_list[0]
        input_tag_list = tag_name_list[1]
        output_tag_list = tag_name_list[2]

        # 設定
        self._setting_dict = setting_dict or {}
        self._use_pref_counter: bool = self._setting_dict["use_pref_counter"]
        waveform_w: int = self._setting_dict.get("waveform_width", 200)
        waveform_h: int = self._setting_dict.get("waveform_height", 400)
        self._default_sampling_rate: int = self._setting_dict.get("default_sampling_rate", 16000)
        self._chunk_size: int = self._setting_dict.get("chunk_size", 1024)

        self._node_data[str(node_id)] = {
            "vad": 0,
            "last_update_time": 0,
        }

        # ノード
        with dpg.node(
            tag=tag_node_name,
            parent=parent,
            label=self.node_label,
            pos=pos,
        ):
            # デバイス状態表示
            with dpg.node_attribute(
                tag=f"{node_id}:status_attr",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                if self._respeaker_device is not None:
                    dpg.add_text("ReSpeaker v2: Connected", color=(0, 255, 0))
                else:
                    dpg.add_text("ReSpeaker v2: Not Found", color=(255, 0, 0))
            
            # VAD出力
            with dpg.node_attribute(
                tag=output_tag_list[0][0],
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_slider_int(
                    tag=output_tag_list[0][1],
                    width=waveform_w - 190,
                    label="Activity (0:OFF 1:ON)",
                    default_value=0,
                    min_value=0,
                    max_value=1,
                    enabled=False,
                )
            
            # 処理時間
            if self._use_pref_counter:
                with dpg.node_attribute(
                    tag=output_tag_list[1][0],
                    attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=output_tag_list[1][1],
                        default_value="elapsed time(ms)",
                    )

        return tag_node_name

    def update(
        self,
        node_id: str,
        connection_list: List[Any],
        player_status_dict: Dict[str, Any],
        node_result_dict: Dict[str, Any],
    ) -> Any:
        tag_name_list: List[Any] = get_tag_name_list(
            node_id,
            self.node_tag,
            [],
            [
                self.TYPE_INT,
                self.TYPE_TIME_MS,
            ],
        )
        output_tag_list = tag_name_list[2]

        # 計測開始
        if self._use_pref_counter:
            start_time = time.perf_counter()

        current_status = player_status_dict.get("current_status", False)
        
        if current_status == "play":
            # 0.1秒毎にVAD更新
            current_time = time.perf_counter()
            if current_time - self._node_data[str(node_id)]["last_update_time"] >= 0.1:
                self._node_data[str(node_id)]["last_update_time"] = current_time
                
                if self._respeaker_device is not None:
                    try:
                        vad = 1 if self._respeaker_device.is_voice() else 0
                        self._node_data[str(node_id)]["vad"] = vad
                        
                        # スライダー更新
                        dpg_set_value(output_tag_list[0][1], vad)
                    except Exception as e:
                        pass
            # 更新間隔内では前回の値を維持（何もしない）

        result_dict = {
            "vad": self._node_data[str(node_id)]["vad"],
        }

        # 計測終了
        if self._use_pref_counter:
            elapsed_time = time.perf_counter() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_tag_list[1][1], str(elapsed_time).zfill(4) + "ms")

        return result_dict

    def close(self, node_id: str) -> None:
        self._add_node_flag = False

    def get_setting_dict(self, node_id: str) -> Dict[str, Any]:
        tag_name_list: List[Any] = get_tag_name_list(
            node_id,
            self.node_tag,
            [],
            [
                self.TYPE_INT,
                self.TYPE_TIME_MS,
            ],
        )
        tag_node_name: str = tag_name_list[0]

        pos: List[int] = dpg.get_item_pos(tag_node_name)

        setting_dict: Dict[str, Any] = {
            "ver": self._ver,
            "pos": pos,
        }
        return setting_dict

    def set_setting_dict(self, node_id: int, setting_dict: Dict[str, Any]) -> None:
        pass