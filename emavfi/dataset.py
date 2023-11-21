import cv2
import os
import os.path as osp
import torch
import numpy as np
import random
from torch.utils.data import Dataset, DataLoader
from config import *
from glob import glob
from natsort import natsorted
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

cv2.setNumThreads(1)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class CO3dDataset(Dataset):
    def __init__(self, root, tg_frames=45, train=True):
        self.train = train
        self.root = root
        self.objects = glob(self.root+'/*/*')
        self.objects = self.objects[:75] if train else self.objects[75:]
        self.triplets = self.get_triplets(self.objects, tg_frames)
        self.h = 256  # ?????????????????
        self.w = 448

    def is_black(self, frame):
        return frame.mean() < 20

    def extract_triplets_from_object(self, total_frames, frames):
        total_imgs = []
        for path in total_frames:
            img = cv2.imread(path)
            if not self.is_black(img):
                total_imgs.append(img)

        triplets = []
        jump = len(total_imgs)//frames
        for i in range(0, len(total_imgs)-jump):
            im1, gt, im2 = total_imgs[i], total_imgs[i +
                                                     jump//2], total_imgs[i+jump]
            im1, gt, im2 = self.aug(im1, gt, im2, 256, 256)
            triplets.append(
                [im1, gt, im2])
        return triplets

    def get_triplets(self, objects, frames):
        triplets = []
        ttype = 'Train' if self.train else 'Test'

        futures = []
        with ThreadPoolExecutor() as exe:
            for obj in objects:
                total_frames = natsorted(glob(osp.join(obj, 'images/*')))
                futures.append(exe.submit(self.extract_triplets_from_object,
                                          total_frames, frames))
            for fut in tqdm(as_completed(futures), desc=f'Loading {ttype} Data Objects', total=len(objects)):
                triplets.extend(fut.result())

        return triplets

    def aug(self, img0, gt, img1, h, w):
        ih, iw, _ = img0.shape
        x = np.random.randint(0, ih - h + 1)
        y = np.random.randint(0, iw - w + 1)
        img0 = img0[x:x+h, y:y+w, :]
        img1 = img1[x:x+h, y:y+w, :]
        gt = gt[x:x+h, y:y+w, :]
        return img0, gt, img1

    def __len__(self):
        return len(self.triplets)

    def __getitem__(self, index):
        img0, gt, img1 = self.triplets[index]

        if self.train:
            img0, gt, img1 = self.aug(img0, gt, img1, 256, 256)
            if random.uniform(0, 1) < 0.5:
                img0 = img0[:, :, ::-1]
                img1 = img1[:, :, ::-1]
                gt = gt[:, :, ::-1]
            if random.uniform(0, 1) < 0.5:
                img1, img0 = img0, img1
            if random.uniform(0, 1) < 0.5:
                img0 = img0[::-1]
                img1 = img1[::-1]
                gt = gt[::-1]
            if random.uniform(0, 1) < 0.5:
                img0 = img0[:, ::-1]
                img1 = img1[:, ::-1]
                gt = gt[:, ::-1]

            p = random.uniform(0, 1)
            if p < 0.25:
                img0 = cv2.rotate(img0, cv2.ROTATE_90_CLOCKWISE)
                gt = cv2.rotate(gt, cv2.ROTATE_90_CLOCKWISE)
                img1 = cv2.rotate(img1, cv2.ROTATE_90_CLOCKWISE)
            elif p < 0.5:
                img0 = cv2.rotate(img0, cv2.ROTATE_180)
                gt = cv2.rotate(gt, cv2.ROTATE_180)
                img1 = cv2.rotate(img1, cv2.ROTATE_180)
            elif p < 0.75:
                img0 = cv2.rotate(img0, cv2.ROTATE_90_COUNTERCLOCKWISE)
                gt = cv2.rotate(gt, cv2.ROTATE_90_COUNTERCLOCKWISE)
                img1 = cv2.rotate(img1, cv2.ROTATE_90_COUNTERCLOCKWISE)

        img0 = torch.from_numpy(img0.copy()).permute(2, 0, 1)
        img1 = torch.from_numpy(img1.copy()).permute(2, 0, 1)
        gt = torch.from_numpy(gt.copy()).permute(2, 0, 1)
        return torch.cat((img0, img1, gt), 0)


# dataset = CO3dDataset('../dataset')
# print(dataset.__len__())
# print(dataset.__getitem__(0).shape)
# sampler = DistributedSampler(dataset)
# train_data = DataLoader(dataset, batch_size=2,
#                         num_workers=1, pin_memory=True, drop_last=True)

# for i, sample in enumerate(train_data):
#     print(sample.shape)
#     exit()

# class VimeoDataset(Dataset):
#     def __init__(self, dataset_name, path, batch_size=32, model="RIFE"):
#         self.batch_size = batch_size
#         self.dataset_name = dataset_name
#         self.model = model
#         self.h = 256
#         self.w = 448
#         self.data_root = path
#         self.image_root = os.path.join(self.data_root, 'sequences')
#         train_fn = os.path.join(self.data_root, 'tri_trainlist.txt')
#         test_fn = os.path.join(self.data_root, 'tri_testlist.txt')
#         with open(train_fn, 'r') as f:
#             self.trainlist = f.read().splitlines()
#         with open(test_fn, 'r') as f:
#             self.testlist = f.read().splitlines()
#         self.load_data()

#     def __len__(self):
#         return len(self.meta_data)

#     def load_data(self):
#         if self.dataset_name != 'test':
#             self.meta_data = self.trainlist
#         else:
#             self.meta_data = self.testlist

#     def aug(self, img0, gt, img1, h, w):
#         ih, iw, _ = img0.shape
#         x = np.random.randint(0, ih - h + 1)
#         y = np.random.randint(0, iw - w + 1)
#         img0 = img0[x:x+h, y:y+w, :]
#         img1 = img1[x:x+h, y:y+w, :]
#         gt = gt[x:x+h, y:y+w, :]
#         return img0, gt, img1

#     def getimg(self, index):
#         imgpath = os.path.join(self.image_root, self.meta_data[index])
#         imgpaths = [imgpath + '/im1.png', imgpath +
#                     '/im2.png', imgpath + '/im3.png']

#         img0 = cv2.imread(imgpaths[0])
#         gt = cv2.imread(imgpaths[1])
#         img1 = cv2.imread(imgpaths[2])
#         return img0, gt, img1

#     def __getitem__(self, index):
#         img0, gt, img1 = self.getimg(index)

#         if 'train' in self.dataset_name:
#             img0, gt, img1 = self.aug(img0, gt, img1, 256, 256)
#             if random.uniform(0, 1) < 0.5:
#                 img0 = img0[:, :, ::-1]
#                 img1 = img1[:, :, ::-1]
#                 gt = gt[:, :, ::-1]
#             if random.uniform(0, 1) < 0.5:
#                 img1, img0 = img0, img1
#             if random.uniform(0, 1) < 0.5:
#                 img0 = img0[::-1]
#                 img1 = img1[::-1]
#                 gt = gt[::-1]
#             if random.uniform(0, 1) < 0.5:
#                 img0 = img0[:, ::-1]
#                 img1 = img1[:, ::-1]
#                 gt = gt[:, ::-1]

#             p = random.uniform(0, 1)
#             if p < 0.25:
#                 img0 = cv2.rotate(img0, cv2.ROTATE_90_CLOCKWISE)
#                 gt = cv2.rotate(gt, cv2.ROTATE_90_CLOCKWISE)
#                 img1 = cv2.rotate(img1, cv2.ROTATE_90_CLOCKWISE)
#             elif p < 0.5:
#                 img0 = cv2.rotate(img0, cv2.ROTATE_180)
#                 gt = cv2.rotate(gt, cv2.ROTATE_180)
#                 img1 = cv2.rotate(img1, cv2.ROTATE_180)
#             elif p < 0.75:
#                 img0 = cv2.rotate(img0, cv2.ROTATE_90_COUNTERCLOCKWISE)
#                 gt = cv2.rotate(gt, cv2.ROTATE_90_COUNTERCLOCKWISE)
#                 img1 = cv2.rotate(img1, cv2.ROTATE_90_COUNTERCLOCKWISE)

#         img0 = torch.from_numpy(img0.copy()).permute(2, 0, 1)
#         img1 = torch.from_numpy(img1.copy()).permute(2, 0, 1)
#         gt = torch.from_numpy(gt.copy()).permute(2, 0, 1)
#         return torch.cat((img0, img1, gt), 0)
