# TP0: Docker + Comunicaciones + Concurrencia

Facundo Baratta - 104886

## Parte 1: Introducción a Docker

### Ejercicio N°1:

Como es sugerido en la solución, `generar-compose.sh` llama a un script de python (creativamente llamado) `generar-compose.py`. El script de bash recibe dos parametros: nombre del archivo de entrada, y de salida. Estos son pasados al script de python. Si la cantidad de variables de entrada es distinta de dos, se muestra ayuda de uso.
El script de python genera un archivo docker-compose con estructura similar al suministrado en el repositorio inicialmente.

Para ejecutarlo:

`./generar-compose.sh <archivo_de_salida> N`

Ejemplo:

`./generar-compose.sh <archivo_de_salida> N`

Luego se puede levantar con el Makefile:

`make docker-compose-up`

### Ejercicio N°2:

Para este ejercicio se montó los archivos de configuración para el servidor y cada cliente respectivamente. Luego, se eliminó las variables de entorno generadas para el .yml para que no pisen a lo seteado en la configuración. Finalmente, se eliminó copiar el archivo de configuración en el Dockerfile. No es necesario ya que se monta como volumen.

### Ejercicio N°3:

El creado script primero genera un string con timestamp único. Luego levanta un contenedor efimero ligero, el cual se conecta a la red de Docker. Con nc se abre un socket TCP al cual se le manda el string, el cual se espera que sea haga un echo idéntico, validando que la red esta saludable.

Luego de levantar los containers y la red como se explica en el ej1, se puede ejecutar el healthcheck minimalista: `./validar-echo-server.sh`

### Ejercicio N°4:

Para el cliente decidí implementar el código de manejo de señales en main.go. Aquí se crea un canal de señales que se subcribe a la señal SIGTERM. Este canal se lo paso como variable la función StartClientLoop, la cual, si hay SIGTERM, crea el log correspondiente y sale de la función, volviendo a main, y finalmente cierra el programa gracefully naturalmente. En ramas posteriores utilizaré una forma más idiomática de corroborar si hay una señal en el canal (mi primera vez programando en Go). Similarmente para el servidor en main.py se subscribe la señal SIGTERM a una función graceful_shutdown. Esta llama a la correspondiente función de mismo nombre del servidor (variable global) - si es que existe, sino corta ejecución del programa. En server.py la función graceful_shutdown cambia el flag que permite seguir recibiendo solicitudes entrantes, e intenta cerrar el socket del servidor y todas las conexiones con los clientes, manejando y logeando los errores que puedan ocurrir.

Luego de levantar los containers se puede enviar la señal SIGTERM de la siguiente manera:
`docker compose -f <filename> stop -t <time>`
Donde `filename` es el nombre del docker compose (no usamos el default sino `docker-compose-dev.yaml`) y `time` los segundos de gracia antes de enviar `SIGKILL`

## Parte 2: Repaso de Comunicaciones

### Ejercicio N°5:

Este ejercicio tal vez tenga la mayor cantidad de código ya que hay que definir el protocolo (inicialmente usé JSON 😿) y toda la lógica de negocio.
En `domain.go` se copia la estructura de apuesta definida en `utils.py` en el servidor y se agrega una funcion que lo parsea de las variable de entorno (que se agregaron al `generar-compose.py` como dummy). Se inicializa con ese helper en `main.go` y se pasa como variable a la función `StartClientLoop`.
`server.py` se modificó para utilizar la lógica de negocio. Se lee la apuesta, se guarda utilizando la función de `utils.py` y se manda un ACK. Se cierra la conexión luego de una única apuesta.

Es en `transfer.go` y `transfer.py` donde se aprecia el protocolo implementando. No es TLV ya que no hay type por campo, pero el Type está implícito en el magic del mensaje y el orden fijo de los campos.
El header son 4 bytes big endian que indican la longitud del payload. Se espera leer o escribir esa longitud luego de leer o escribir esos 4 bytes. De esta forma, evito errores de short read/write.
Luego, se manda un "MAGIC" string de también 4 bytes que indica el tipo de mensaje. Aquí, es BET0 o ACK0.

El formato BET es el siguiente:

```
"BET0"
[agency: u16 BE]
[first_name: u16 len][bytes...]
[last_name : u16 len][bytes...]
[document : u16 len][bytes...]
[birthdate : 10 bytes ASCII "YYYY-MM-DD"]
[number : u32 BE]
```

Y el del ACK:

```
"ACK0"
[ok: 1 byte 0|1]
[si ok==0 => error: u16 len + bytes]
```

Se levanta como en el primer ejercico

### Ejercicio N°7:

Para este ejercicio se agrego más tipos de mensajes: DONE (finalizó de mandar todos lo batches), QWIN (el cliente query de wins de su agencia), y WINS (el servidor le manda los ganadores de su agencia en particular)

Moví la lógica de procesar los mensajes a `process.py`. Aquí se hace un pequeño peek al magic. Dependiendo de lo que manda el cliente (BCH0, DONE, QWIN), se guarda apuestas, se encola para responder ganadores, o se procede a hacer la votación. Esta última depende de si llegaron tantos DONE como se esperaban.

Se levanta como en el primer ejercicio

## Parte 3: Repaso de Concurrencia

### Ejercicio N°8:

En `server/common/server.py` uso `multiprocessing` y levanto un proceso por conexión aceptada. Así evito el GIL y puedo procesar en paralelo sin bloquear el resto. Para este trabajo con mucho I/O blocking sería justificable, pero lo evité de todas maneras.
Coordino entre procesos con un `Manager()` (diccionarios compartidos para `done_agencies` y `winners_by_agency`) y un `Event` para marcar cuándo terminó el sorteo, con la lógica de mensajes todavía en `server/common/process.py`.
Hago `terminate/join` de workers y `manager.shutdown()` para liberar recursos. También voy “recolectando” (join) procesos terminados en el loop de `accept` para que no queden zombies.
Para este ejercicio modifiqué `server/common/utils.py`: agregé `fcntl.flock` (LOCK_EX/LOCK_SH) sobre `bets.csv` para serializar escrituras y evitar lecturas parciales entre procesos. Hago `flush()` y `fsync()` al terminar de escribir.
No cambia el protocolo ni los logs pedidos; sólo se paraleliza el manejo y se endurece la E/S y la persistencia.

Se levanta como en el primer ejericio...
