from time import time
from tqdm import tqdm
from Data import *
from ResNet import ResNet
import torch
from torch.optim.optimizer import Optimizer
import torch.nn as nn
from typing import Type, Union, List, Optional, Callable, Any
from utils import EarlyStopper
from utils import Plotter 

class Train:
    def __init__(self):
        self.best_acc = 0

    def train(
            self, 
            epoch: int,
            model: ResNet, 
            device: torch.device,
            criterion: Type[nn.Module],
            optimizer: Optimizer,
            train_loader: Type[DataLoader]
            ) -> Union[float, float]:
        train_loss = correct_preds = total = 0
        model.to(device)
        model.train()
        start = time()
        for batch, (inputs, labels) in enumerate(train_loader):
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs,labels)
            optimizer.step()

            train_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct_preds = predicted.eq(labels).sum().item()
        end = time()
        train_accuracy = 100. * correct_preds / total
        print("########################################################################################################################")
        print(f'Epoch: {epoch} | Train Loss: {train_loss/(batch + 1)} | Train Accuracy: {train_accuracy} | Time Elapsed: {end-start}sec')

        return train_accuracy, train_loss
    
    def test(
            self, 
            epoch: int,
            model: ResNet, 
            device: torch.device,
            criterion: Type[nn.Module],
            test_loader: Type[DataLoader],
            option: str, # Test or Validation
            ) -> Union[float, float]:
        test_loss = correct_preds = total = 0
        start = time()
        with torch.no_grad():
            for batch, (inputs, labels) in enumerate(test_loader):
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs,labels)

                test_loss += loss.item()
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct_preds = predicted.eq(labels).sum().item()
        end = time()
        test_accuracy = 100. * correct_preds / total
        print(f'Epoch: {epoch} | {option} Loss: {test_loss/(batch + 1)} | {option} Accuracy: {test_accuracy} | Time Elapsed: {end-start}sec')
        print("############################################################################################################################")
        if test_accuracy > self.best_acc:
            model.cpu()
            model_scripted = torch.jit.script(model)
            try:
                model_scripted.save('./saved_models/ResNet.pt')
                print("Saved Model")
                self.best_acc = test_accuracy
            except FileNotFoundError:
                os.makedirs('./saved_models', exist_ok=True)
                model_scripted.save('./saved_models/ResNet.pt')
                print("Directory didn't exist. Created directory and saved model.")
                self.best_acc = test_accuracy

        return test_accuracy, test_loss
    
    def run(
            self, 
            epochs: int, 
            model: ResNet, 
            device: torch.device, 
            criterion: Type[nn.Module],
            optimizer: Optimizer,
            scheduler: torch.optim.lr_scheduler, 
            trainloader: Type[DataLoader], 
            testloader: Type[DataLoader], 
            option: str,
            early_stopper: EarlyStopper = EarlyStopper(),
            patience: int = 5,
            ):
        train_loss_history = train_acc_history = val_loss_history = val_acc_history = []
        for epoch in tqdm(range(epochs)):
            train_acc, train_loss = self.train(epoch, model, device, criterion, optimizer, trainloader)
            val_acc, val_loss = self.test(epoch, model, device, criterion, testloader, option)
            scheduler.step()

            train_loss_history.append(train_loss)
            train_acc_history.append(train_acc)
            val_loss_history.append(val_loss)
            val_acc_history.append(val_acc)

            if early_stopper.early_stop(val_loss):
                print(f"Early stopping triggered after {epoch} epochs")
                break
        
        plot = Plotter()
        plot.plot_train_loss(train_losses=train_loss_history, epochs=range(epochs))
        plot.plot_train_accuracy(train_accuracies=train_acc_history, epochs=range(epochs))
        plot.plot_loss_comparison(train_losses=train_loss_history, val_losses=val_loss_history, epochs=range(epochs))
        plot.plot_accuracy_comparison(train_accuracies=train_acc_history, val_accuracies=val_acc_history, epochs=range(epochs))