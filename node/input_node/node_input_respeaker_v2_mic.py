#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
from typing import Any, Dict, List, Optional

import dearpygui.dearpygui as dpg  # type: ignore
import numpy as np
import sounddevice as sd  # type: ignore
from node_editor.util import dpg_set_value, get_tag_name_list  # type: ignore

from node.node_abc import DpgNodeABC  # type: ignore


class Node(DpgNodeABC):
    _ver: str = "0.0.1"

    node_label: str = "ReSpeaker v2 Mic"
    node_tag: str = "ReSpeakerV2Mic"
    
    # クラス変数として共有ストリームを管理
    _respeaker_sd = None
    _respeaker_buffer = None
    _shared_node_count = 0
    _shared_chunks = [np.array([]) for _ in range(6)]
    _shared_chunk_updated = False
    _processed_node_count = 0

    def __init__(self) -> None:
        self._node_data = {}

        # ReSpeakerオーディオデバイスを探す
        self._respeaker_input_id = None
        
        # デバイスリストからReSpeakerを探す
        for input_id, device in enumerate(sd.query_devices()):
            if device["max_input_channels"] >= 6 and "ReSpeaker" in device["name"]:
                self._respeaker_input_id = input_id
                break

    def add_node(
        self,
        parent: str,
        node_id: int,
        pos: List[int] = [0, 0],
        setting_dict: Optional[Dict[str, Any]] = None,
        callback: Optional[Any] = None,
    ) -> str:
        # タグ名
        tag_name_list: List[Any] = get_tag_name_list(
            node_id,
            self.node_tag,
            [self.TYPE_TEXT],
            [
                self.TYPE_SIGNAL_CHUNK,
                self.TYPE_TIME_MS,
            ],
        )
        tag_node_name: str = tag_name_list[0]
        input_tag_list = tag_name_list[1]
        output_tag_list = tag_name_list[2]

        # 設定
        self._setting_dict = setting_dict or {}
        waveform_w: int = self._setting_dict.get("waveform_width", 200)
        waveform_h: int = self._setting_dict.get("waveform_height", 400)
        self._default_sampling_rate: int = self._setting_dict.get(
            "default_sampling_rate", 16000
        )
        self._chunk_size: int = self._setting_dict.get("chunk_size", 1024)
        self._use_pref_counter: bool = self._setting_dict["use_pref_counter"]

        self._node_data[str(node_id)] = {
            "buffer": np.array([]),
            "chunks": [np.array([]) for _ in range(6)],
            "chunk_index": -1,
            "display_x_buffer": np.array([]),
            "display_y_buffer": np.array([]),
            "selected_channel": 0,
            "is_stopped": False,  # 停止処理の実行フラグ
            "is_master": Node._shared_node_count == 0,  # 最初のノードがマスター
        }
        
        # 共有ノード数をカウント
        Node._shared_node_count += 1

        # 表示用バッファ用意（1チャンネル分）
        buffer_len: int = int(self._default_sampling_rate * 5)  # 5秒分
        self._node_data[str(node_id)]["display_y_buffer"] = np.zeros(
            buffer_len, dtype=np.float32
        )
        self._node_data[str(node_id)]["display_x_buffer"] = (
            np.arange(buffer_len) / self._default_sampling_rate
        )

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
                if self._respeaker_input_id is not None:
                    dpg.add_text("ReSpeaker v2: Connected", color=(0, 255, 0))
                else:
                    dpg.add_text("ReSpeaker v2: Not Found", color=(255, 0, 0))
            
            # チャンネル選択
            with dpg.node_attribute(
                tag=input_tag_list[0][0],
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                channel_names: List[str] = [
                    "AEC + Beamformed",  # Ch0
                    "Mic #1 (raw)",      # Ch1
                    "Mic #2 (raw)",      # Ch2
                    "Mic #3 (raw)",      # Ch3
                    "Mic #4 (raw)",      # Ch4
                    "Playback Reference" # Ch5
                ]
                dpg.add_combo(
                    channel_names,
                    default_value=channel_names[0],
                    width=waveform_w,
                    tag=input_tag_list[0][1],
                    callback=self._on_channel_select,
                )
            
            # プロットエリア
            with dpg.node_attribute(
                tag=output_tag_list[0][0],
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                with dpg.plot(
                    height=waveform_h,
                    width=waveform_w,
                    no_inputs=False,
                    tag=f"{node_id}:audio_plot_area",
                ):
                    dpg.add_plot_axis(
                        dpg.mvXAxis,
                        label="Time(s)",
                        no_label=True,
                        no_tick_labels=True,
                        tag=f"{node_id}:xaxis",
                    )
                    dpg.add_plot_axis(
                        dpg.mvYAxis,
                        label="Amplitude",
                        no_label=True,
                        no_tick_labels=True,
                        tag=f"{node_id}:yaxis",
                    )
                    dpg.set_axis_limits(f"{node_id}:xaxis", 0.0, 5.0)
                    dpg.set_axis_limits(f"{node_id}:yaxis", -1.0, 1.0)

                    dpg.add_line_series(
                        [],
                        [],
                        parent=f"{node_id}:yaxis",
                        tag=f"{node_id}:audio_line_series",
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

    def _on_channel_select(self, sender, app_data, user_data):
        """チャンネル選択時のコールバック"""
        node_id = sender.split(":")[0]
        
        # チャンネル名からインデックスに変換
        channel_names = [
            "AEC + Beamformed",  # Ch0
            "Mic #1 (raw)",      # Ch1
            "Mic #2 (raw)",      # Ch2
            "Mic #3 (raw)",      # Ch3
            "Mic #4 (raw)",      # Ch4
            "Playback Reference" # Ch5
        ]
        selected_channel = channel_names.index(app_data)
        
        if node_id in self._node_data:
            self._node_data[node_id]["selected_channel"] = selected_channel

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
            [self.TYPE_TEXT],
            [
                self.TYPE_SIGNAL_CHUNK,
                self.TYPE_TIME_MS,
            ],
        )
        output_tag_list = tag_name_list[2]

        # 計測開始
        if self._use_pref_counter:
            start_time = time.perf_counter()

        # 再生に合わせてスクロールし、チャンク取り出しを行う
        chunks: List[np.ndarray] = [np.array([]) for _ in range(6)]
        current_status = player_status_dict.get("current_status", False)
        
        if current_status == "play":
            # 再生開始時にフラグをリセット
            self._node_data[str(node_id)]["is_stopped"] = False
            
            # 共有マイクストリーム開始
            if Node._respeaker_sd is None and self._respeaker_input_id is not None:
                # 共有バッファを初期化
                Node._respeaker_buffer = np.zeros((0, 6), dtype=np.float32)
                
                def shared_callback_mic(indata, frames, time_info, status):
                    if status:
                        print(status)
                    # 共有バッファに追加
                    if len(Node._respeaker_buffer) == 0:
                        Node._respeaker_buffer = indata.copy()
                    else:
                        Node._respeaker_buffer = np.concatenate(
                            (Node._respeaker_buffer, indata)
                        )

                Node._respeaker_sd = sd.InputStream(
                    samplerate=self._default_sampling_rate,
                    channels=6,
                    blocksize=self._chunk_size,
                    device=self._respeaker_input_id,
                    dtype="float32",
                    callback=shared_callback_mic,
                )
                Node._respeaker_sd.start()

            # マスターノードがチャンク処理を担当
            if self._node_data[str(node_id)]["is_master"]:
                # 個別バッファに共有バッファからコピー
                if Node._respeaker_buffer is not None and len(Node._respeaker_buffer) >= self._chunk_size:
                    buf = self._node_data[node_id]["buffer"]
                    if len(buf) == 0:
                        self._node_data[node_id]["buffer"] = Node._respeaker_buffer.copy()
                    else:
                        self._node_data[node_id]["buffer"] = np.concatenate(
                            (buf, Node._respeaker_buffer)
                        )
                    # 共有バッファをクリア
                    Node._respeaker_buffer = np.zeros((0, 6), dtype=np.float32)

                if len(self._node_data[node_id]["buffer"]) >= self._chunk_size:
                    # チャンク取り出し（6チャンネル分）
                    chunk_data = self._node_data[node_id]["buffer"][: self._chunk_size]
                    for ch in range(6):
                        chunks[ch] = chunk_data[:, ch]
                        # 共有チャンクに保存
                        Node._shared_chunks[ch] = chunks[ch].copy()
                    
                    self._node_data[node_id]["buffer"] = self._node_data[node_id]["buffer"][
                        self._chunk_size :
                    ]
                    
                    # チャンクインデックス更新
                    self._node_data[str(node_id)]["chunk_index"] += 1
                    # 共有チャンク更新フラグを立てる
                    Node._shared_chunk_updated = True
                    Node._processed_node_count = 0
            else:
                # スレーブノードは共有チャンクが更新された時のみ処理
                if Node._shared_chunk_updated:
                    for ch in range(6):
                        chunks[ch] = Node._shared_chunks[ch].copy()
                        self._node_data[node_id]["chunks"][ch] = chunks[ch]
                    
                    # チャンクインデックス更新
                    self._node_data[str(node_id)]["chunk_index"] += 1

            # プロット更新（チャンクがある場合のみ）
            if len(chunks[0]) > 0:
                selected_ch = self._node_data[str(node_id)]["selected_channel"]
                temp_display_y_buffer = self._node_data[str(node_id)]["display_y_buffer"]
                temp_display_y_buffer = np.roll(temp_display_y_buffer, -self._chunk_size)
                temp_display_y_buffer[-self._chunk_size:] = chunks[selected_ch]
                self._node_data[str(node_id)]["display_y_buffer"] = temp_display_y_buffer
                
                dpg.set_value(
                    f"{node_id}:audio_line_series",
                    [
                        self._node_data[str(node_id)]["display_x_buffer"],
                        temp_display_y_buffer,
                    ],
                )
                
                # 処理したノード数をカウント
                Node._processed_node_count += 1
                
                # 全ノードが処理完了したらフラグをリセット
                if Node._processed_node_count >= Node._shared_node_count:
                    Node._shared_chunk_updated = False
                
        elif current_status == "pause":
            pass
        elif current_status == "stop":
            # 停止処理は一度だけ実行
            if not self._node_data[str(node_id)]["is_stopped"]:
                self._node_data[str(node_id)]["is_stopped"] = True
                
                # バッファ初期化
                self._node_data[str(node_id)]["buffer"] = np.zeros((0, 6), dtype=np.float32)
                self._node_data[str(node_id)]["chunk_index"] = -1

                # プロットエリア初期化
                buffer_len: int = int(self._default_sampling_rate * 5)
                self._node_data[str(node_id)]["display_y_buffer"] = np.zeros(
                    buffer_len, dtype=np.float32
                )
                self._node_data[str(node_id)]["display_x_buffer"] = (
                    np.arange(buffer_len) / self._default_sampling_rate
                )
                dpg.set_value(
                    f"{node_id}:audio_line_series",
                    [
                        self._node_data[str(node_id)]["display_x_buffer"].tolist(),
                        list(self._node_data[str(node_id)]["display_y_buffer"]),
                    ],
                )

            # 最後のノードが停止時のみ共有ストリームを閉じる
            if Node._shared_node_count == 1 and Node._respeaker_sd is not None:
                Node._respeaker_sd.close()
                Node._respeaker_sd = None
                Node._respeaker_buffer = None

        # 選択されたチャンネルのチャンクを出力
        selected_ch = self._node_data[str(node_id)]["selected_channel"]
        if len(chunks[selected_ch]) > 0:
            output_chunk = chunks[selected_ch]
        else:
            output_chunk = self._node_data[node_id]["chunks"][selected_ch]
        
        result_dict = {
            "chunk_index": self._node_data[str(node_id)].get("chunk_index", -1),
            "chunk": output_chunk,
        }

        # 計測終了
        if self._use_pref_counter:
            elapsed_time = time.perf_counter() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_tag_list[1][1], str(elapsed_time).zfill(4) + "ms")

        return result_dict

    def close(self, node_id: str) -> None:
        # ノードカウントを減らす
        Node._shared_node_count -= 1
        
        # 最後のノードが閉じられる場合、共有ストリームも閉じる
        if Node._shared_node_count <= 0:
            if Node._respeaker_sd is not None:
                Node._respeaker_sd.close()
                Node._respeaker_sd = None
                Node._respeaker_buffer = None
                Node._shared_chunks = [np.array([]) for _ in range(6)]
                Node._shared_chunk_updated = False
                Node._processed_node_count = 0
            Node._shared_node_count = 0
        
        self._node_data[str(node_id)]["buffer"] = np.zeros((0, 6), dtype=np.float32)

    def get_setting_dict(self, node_id: str) -> Dict[str, Any]:
        tag_name_list: List[Any] = get_tag_name_list(
            node_id,
            self.node_tag,
            [self.TYPE_TEXT],
            [
                self.TYPE_SIGNAL_CHUNK,
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