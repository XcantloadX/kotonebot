# 此脚本用于读入 extract_schema.py 生成的数据库文件，
# 并下载对应的资源

import os
import sys
import tqdm
import shutil
import sqlite3

import cv2

sys.path.append(os.path.abspath('./submodules/GkmasObjectManager'))

import GkmasObjectManager as gom # type: ignore

print("拉取资源...")
manifest = gom.fetch()

print("提取 P 偶像卡资源...")
base_path = './kotonebot/kaa/resources/idol_cards'
os.makedirs(base_path, exist_ok=True)

db = sqlite3.connect("./kotonebot/kaa/resources/game.db")
cursor = db.execute("""
SELECT
    IC.id AS cardId,
    ICS.id AS skinId,
    Char.lastName || ' ' || Char.firstName || ' - ' || IC.name AS name,
    ICS.assetId,
    -- アナザー 版本偶像相关
    NOT (IC.originalIdolCardSkinId = ICS.id) AS isAnotherVer,
    ICS.name AS anotherVerName
FROM IdolCard IC
JOIN Character Char ON characterId = Char.id
JOIN IdolCardSkin ICS ON IC.id = ICS.idolCardId;
""")

print("下载 P 偶像卡资源...")
for row in tqdm.tqdm(cursor.fetchall()):
    _, skin_id, name, asset_id, _, _ = row

    # 下载资源
    # 低特训等级
    asset_id0 = f'img_general_{asset_id}_0-thumb-portrait'
    path0 = base_path + f'/{skin_id}_0.png'
    # 高特训等级
    asset_id1 = f'img_general_{asset_id}_1-thumb-portrait'
    path1 = base_path + f'/{skin_id}_1.png'
    if asset_id is None:
        raise ValueError(f"未找到P偶像卡资源：{skin_id} {name}")
    if not os.path.exists(path0):
        manifest.download(asset_id0, path=path0, categorize=False)
        # 转换分辨率 140x188
        img0 = cv2.imread(path0)
        assert img0 is not None
        img0 = cv2.resize(img0, (140, 188), interpolation=cv2.INTER_AREA)
        cv2.imwrite(path0, img0)
    if not os.path.exists(path1):
        manifest.download(asset_id1, path=path1, categorize=False)
        # 转换分辨率 140x188
        img1 = cv2.imread(path1)
        assert img1 is not None
        img1 = cv2.resize(img1, (140, 188), interpolation=cv2.INTER_AREA)
        cv2.imwrite(path1, img1)
