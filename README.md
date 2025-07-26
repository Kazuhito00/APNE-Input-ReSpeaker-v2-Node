> [!WARNING]
> APNE-Input-ReSpeaker-v2-Node は [Audio-Processing-Node-Editor](https://github.com/Kazuhito00/Audio-Processing-Node-Editor) の追加用ノードです。<br>
> このリポジトリ単体では動作しません。

# APNE-Input-ReSpeaker-v2-Node
[Audio-Processing-Node-Editor](https://github.com/Kazuhito00/Audio-Processing-Node-Editor) で動作する[ReSpeaker v2](https://jp.seeedstudio.com/ReSpeaker-USB-Mic-Array-p-4247.html)入力用ノードです。<br>
6チャンネル（AEC、マイク1～4、リファレンス音源）と、VAD、DOAのノードを用意しています。<br>
なお、DOAやVADの感度調整やオプション変更には対応していません。

<img width="1648" height="1080" alt="image" src="https://github.com/user-attachments/assets/71bd33bf-5d72-4cbb-8881-41e42d13d114" />


# Requirement
[Audio-Processing-Node-Editor](https://github.com/Kazuhito00/Audio-Processing-Node-Editor) の依存パッケージに加えて、以下のパッケージのインストールが必要です。
```
pip install pyusb  ※ VADやDOAを利用する場合
```

# Installation
* UbuntuやMacはドライバインストールなどは不要ですが、WindowsでVADやDOAを利用する場合インストールが必要です<br>必要に応じて[Wiki](https://wiki.seeedstudio.com/ja/ReSpeaker_Mic_Array_v2.0/#dfu%E3%81%8A%E3%82%88%E3%81%B3led%E5%88%B6%E5%BE%A1%E3%83%89%E3%83%A9%E3%82%A4%E3%83%90%E3%83%BC%E3%81%AE%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB)を参照してインストールしてください
* node ディレクトリを [Audio-Processing-Node-Editor](https://github.com/Kazuhito00/Audio-Processing-Node-Editor) の [node](https://github.com/Kazuhito00/Audio-Processing-Node-Editor/tree/main/node) ディレクトリにコピーしてください。

# Node
<details open>
<summary>Input Node</summary>

<table>
    <tr>
        <td width="200">
            ReSpeaker v2 Mic
        </td>
        <td width="320">
            <img src="https://github.com/user-attachments/assets/0177158c-6f66-4a42-9897-1115ef1ef96b" loading="lazy" width="300px">
        </td>
        <td width="760">
            ReSpeaker v2のマイク入力を扱うノード<br>
            ドロップダウンリストから、使用したいマイク入力を選択してください。
        </td>
    </tr>
    <tr>
        <td width="200">
            ReSpeaker v2 DOA
        </td>
        <td width="320">
            <img src="https://github.com/user-attachments/assets/1dffc29f-c1b8-4dbd-8863-05644f77f3af" loading="lazy" width="300px">
        </td>
        <td width="760">
            ReSpeaker v2のDOA機能を扱うノード
        </td>
    </tr>
    <tr>
        <td width="200">
            ReSpeaker v2 Mic
        </td>
        <td width="320">
            <img src="https://github.com/user-attachments/assets/7c88dc94-78e7-4ade-b29f-d7c8f8cab9b1" loading="lazy" width="300px">
        </td>
        <td width="760">
            ReSpeaker v2のVAD機能を扱うノード
        </td>
    </tr>
</table>

</details>

# Reference
* [Wiki](https://wiki.seeedstudio.com/ja/ReSpeaker_Mic_Array_v2.0/#dfu%E3%81%8A%E3%82%88%E3%81%B3led%E5%88%B6%E5%BE%A1%E3%83%89%E3%83%A9%E3%82%A4%E3%83%90%E3%83%BC%E3%81%AE%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB)
* [respeaker/usb_4_mic_array](https://github.com/respeaker/usb_4_mic_array)

# Author
高橋かずひと(https://twitter.com/KzhtTkhs)
 
# License 
APNE-Input-ReSpeaker-v2-Node is under [Apache-2.0 license](LICENSE).<br><br>
