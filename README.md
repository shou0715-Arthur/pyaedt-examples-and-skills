# PyAEDT examples and skills

這是 2026-11-02 整理的 PyAEDT 範例與 AI agent skill 快照。檔案保留原始碼；來源、版本與授權列於下方。這不是 Ansys 官方發行版，也不會自動追蹤上游更新。

## 範例程式

| 用途 | 本庫檔案 | 原始來源 |
| --- | --- | --- |
| HFSS 半波偶極天線與遠場分析 | [dipole.py](examples/high_frequency/antenna/dipole.py) | [Ansys 原始碼](https://github.com/ansys/pyaedt-examples/blob/21c5d1f23d2740c275715c08f454f2a92fbc41ef/examples/high_frequency/antenna/dipole.py) |
| HFSS 探針饋入貼片天線 | [patch.py](examples/high_frequency/antenna/patch.py) | [Ansys 原始碼](https://github.com/ansys/pyaedt-examples/blob/21c5d1f23d2740c275715c08f454f2a92fbc41ef/examples/high_frequency/antenna/patch.py) |
| Maxwell 2D 永磁同步馬達暫態分析 | [pm_synchronous.py](examples/low_frequency/motor/aedt_motor/pm_synchronous.py) | [Ansys 原始碼](https://github.com/ansys/pyaedt-examples/blob/21c5d1f23d2740c275715c08f454f2a92fbc41ef/examples/low_frequency/motor/aedt_motor/pm_synchronous.py) |
| Icepak 顯示卡熱分析 | [graphic_card.py](examples/electrothermal/graphic_card.py) | [Ansys 原始碼](https://github.com/ansys/pyaedt-examples/blob/21c5d1f23d2740c275715c08f454f2a92fbc41ef/examples/electrothermal/graphic_card.py) |

這四個檔案來自 [ansys/pyaedt-examples](https://github.com/ansys/pyaedt-examples/tree/21c5d1f23d2740c275715c08f454f2a92fbc41ef)。完整範例與解說請參考 [PyAEDT Examples](https://examples.aedt.docs.pyansys.com/version/dev/examples/aedt/index.html)。範例可能下載額外資料，也需要對應的 AEDT、PyAEDT 與求解器環境。

## Skills

| 用途 | 本庫目錄 | 原始來源 |
| --- | --- | --- |
| 官方 PyAEDT CLI：AEDT session、project、script、export 操作 | [pyaedt-cli](skills/pyaedt-cli/) | [ansys/pyaedt](https://github.com/ansys/pyaedt/tree/0b95b07a36f3b966290d289ffab655ebb8df5900/.github/plugin/pyaedt-cli/skills) |
| HFSS 基本專案建立、分析與 Touchstone 匯出 | [hfss-api-skill](skills/hfss-api-skill/) | [LZT001107/hfss-api-skill](https://github.com/LZT001107/hfss-api-skill/tree/cd40d035ab1a22ec42cb59005e5d5a9ef4208461) |
| HFSS 天線 S 參數、遠場與參數掃描模板 | [pyaedt-hfss-antenna](skills/pyaedt-hfss-antenna/) | [tuzengji/pyaedt-hfss-antenna](https://github.com/tuzengji/pyaedt-hfss-antenna/tree/09e75e405e7ccb2f69770bf8d70af3433c45c14e) |
| Maxwell 2D/3D 與馬達工作流程 | 僅收錄來源連結 | [Justin-618/ansys-maxwell-skill](https://github.com/Justin-618/ansys-maxwell-skill/tree/f64b8c811ad8a514d80c77fa8f51a7d14a96c16a) |

Maxwell skill 上游未提供授權檔，因此本庫沒有複製其程式與文件。上述其他 skill 的配套腳本、模板及參考文件已一併收錄。執行前請先檢查本機 AEDT 與 PyAEDT 版本，並核對目前的 API／CLI 說明。

## 授權與來源

本庫複製的第三方內容分別依其原始 MIT 授權提供，授權全文保存在 [licenses](licenses/)：

- [PyAEDT Examples](licenses/ansys-pyaedt-examples-LICENSE)
- [PyAEDT](licenses/ansys-pyaedt-LICENSE)
- [HFSS API Skill](licenses/lzt001107-hfss-api-skill-LICENSE)
- [PyAEDT HFSS Antenna](licenses/tuzengji-pyaedt-hfss-antenna-LICENSE)

各來源的 commit 已固定在上方連結中。此庫只保存列出的檔案快照；更新時應重新核對上游內容與授權。
