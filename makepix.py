import cv2
import os
import os.path as osp
import torch
import numpy as np
import random
from torch.utils.data import Dataset, DataLoader

# from config import *
from glob import glob
from natsort import natsorted
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from torchvision.utils import save_image
from utils import *
cv2.setNumThreads(1)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

from Trainer import Model


class CO3dDataset(Dataset):
    def __init__(self, root, tg_frames, in_size, multi, train):
        self.train = "train" if train else "test"
        self.root = root
        self.in_size = in_size
        self.tg_frames = tg_frames
        self.multi = multi
        # print(glob(self.root + f"/{self.train}/*"))
        self.objects = glob(self.root + f"/{self.train}/*") + glob(self.root + f"/test/*")
        self.packs = self.get_packs(self.objects)
        # print(self.packs[:2])
        # if train:
        #     random.shuffle(self.packs)
        # self.triplets = self.get_triplets(self.objects, tg_frames)
        self.h = 256  # ?????????????????
        self.w = 448

    def get_packs(self, objects):
        packs = []
        for obj in objects:
            ims = natsorted(glob(obj + "/images/*"))
            pack_size = len(ims) // self.tg_frames
            if pack_size <= 0:
                continue
            for i in range(0, len(ims) - pack_size, pack_size):
                packs.append(ims[i : i + pack_size])
        return packs

    def aug(self, img0, gt, img1, h, w, train=True):
        img0 = cv2.resize(img0, (w, h))
        gt = cv2.resize(gt, (w, h))
        img1 = cv2.resize(img1, (w, h))
        return img0, gt, img1

    def __len__(self):
        return len(self.packs)

    def __getitem__(self, index):
        pack = self.packs[index]
        times = []
        for i in range(1, len(pack)-1):
            times.append((i - 0) * 1.0 / (len(pack) -1 + 1e-6))
        return (pack, times)
        # img0 = cv2.imread(pack[0])
        # # gt = cv2.imread(pack[ind[1]])
        # img1 = cv2.imread(pack[-1])


        # img0 = torch.from_numpy(img0.copy()).permute(2, 0, 1)
        # img1 = torch.from_numpy(img1.copy()).permute(2, 0, 1)

        # img0, gt, img1 = self.aug(img0, gt, img1, self.in_size, self.in_size)

        # return torch.cat((img0, img1, gt), 0), timestep


def convert(param):
    return {k.replace("module.", ""): v for k, v in param.items() if "module." in k and "attn_mask" not in k and "HW" not in k}


if __name__ == "__main__":
    dataset = CO3dDataset("../dataset/dataset", 18, 350, multi=True, train=True)

    for item in dataset:
        pack = item[0]
        times = item[1]
        print(pack, times)
        # break
        I0 = cv2.imread(pack[0])
        I2 = cv2.imread(pack[-1])

        I0_ = (torch.tensor(I0.transpose(2, 0, 1)).cuda() / 255.).unsqueeze(0)
        I2_ = (torch.tensor(I2.transpose(2, 0, 1)).cuda() / 255.).unsqueeze(0)
        padder = InputPadder(I0_.shape, divisor=32)
        I0_, I2_ = padder.pad(I0_, I2_)
        preds = model.multi_inference(I0_, I2_, TTA=TTA, time_list= times, fast_TTA=TTA)
        print(preds.shape)
        break
    # net = Model(0)
    # net.load_state_dict(net.convert(torch.load(f"../infer_models/emavfi/ours_small_t.pkl")))
    # for _, imgs in enumerate(val_data):
    #     imgs = imgs.to(device, non_blocking=True) / 255.0
    #     imgs, gt = imgs[:, 0:6], imgs[:, 6:]
    #     with torch.no_grad():
    #         pred, _ = model.update(imgs, gt, training=False)
    # print(dataset.__len__())
    # for i in range(5):
    # item = dataset.__getitem__(0)
    # print(item)
    #     print(item[0].shape, item[1])
