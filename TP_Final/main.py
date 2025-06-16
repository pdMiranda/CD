import os
import torch
import torch.nn as nn
import torch.optim as optim
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, TensorDataset
from torch.utils.data.distributed import DistributedSampler
from utils import ComplexNeuralNetwork, generate_dummy_data, evaluate_model

def cleanup():
    dist.destroy_process_group()

def run_ddp_training(rank, world_size, master_addr, master_port, num_epochs=10):
    print(f"Process {rank}: Inicializando...")
    
    dist.init_process_group(
        backend="gloo",
        init_method=f"tcp://{master_addr}:{master_port}",
        rank=rank,
        world_size=world_size
    )

    print(f"Process {rank}: Process group inicializado.")


    X_train, y_train, X_test, y_test = generate_dummy_data() 
    input_dim = X_train.shape[1]
    output_dim = 1

    train_dataset = TensorDataset(X_train, y_train)
    train_sampler = DistributedSampler(train_dataset, num_replicas=world_size, rank=rank)

    train_dataloader = DataLoader(train_dataset, batch_size=64, sampler=train_sampler) 


    model = ComplexNeuralNetwork(input_dim, hidden_dim1=128, hidden_dim2=64, output_dim=output_dim)
    model = DDP(model)

    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001) 

    print(f"Process {rank}: Iniciando treinamento com ComplexNeuralNetwork...")
    for epoch in range(num_epochs):
        train_sampler.set_epoch(epoch) 
        model.train()
        for i, (inputs, labels) in enumerate(train_dataloader):
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            if i % 10 == 0:
                print(f"\nProcess {rank}: Epoch {epoch+1}, Batch {i+1}/{len(train_dataloader)}, Loss: {loss.item():.4f}")

        if rank == 0:
            dist.barrier() 
            accuracy = evaluate_model(model.module, X_test, y_test)
            print(f"Process {rank}: Epoch {epoch+1}, Acuracia de teste: {accuracy:.4f}")
        else:
            dist.barrier()

    print(f"Process {rank}: Treinamento concluído.\n")
    cleanup()

if __name__ == "__main__":
    rank = int(os.environ["RANK"])
    world_size = int(os.environ["WORLD_SIZE"])
    master_addr = os.environ["MASTER_ADDR"]
    master_port = os.environ["MASTER_PORT"]

    run_ddp_training(rank, world_size, master_addr, master_port)