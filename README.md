tubolinea
=========

**tubolinea** è un piccolo script che permette di creare pipelines
di programmi python operanti su ambienti conda diversi sfruttando
il meccanismo della POSIX Shared Memory su Linux

il tool comprende una mini-cli
```
python3 tubolinea.py create path/to/project
```
che crea il file `__tubolinea__.py` 

all'interno del file l'utente modifica la funzione `Func()` a suo 
piacimento.

Si include il file `tubolinea.py` nel proprio programma 
e si esegue `run(path)` per eseguire `Func()`

il file `__tubolinea__.py` viene eseguito come sottoprocesso,
eseguendo la funzione `Func(arg)` che eventualmente ritornerà 
un valore `value`. 

Vengono create 3 istanze di shared memory:
il processo padre ne crea due:
- una per passare l'argomento alla funzione
- una per ricevere il nome della terza shared memory

il processo figlio dopo aver eseguito `Func` e aver
ottenuto il valore di ritorna crea:
- una shared memory per passare il valore di ritorno della funzione
e scrive il nome di questa shared memory nella seconda shared memory 
passatagli dal padre
