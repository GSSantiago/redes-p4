class CamadaEnlace:
    ignore_checksum = False

    def __init__(self, linhas_seriais):
        """
        Inicia uma camada de enlace com um ou mais enlaces, cada um conectado
        a uma linha serial distinta. O argumento linhas_seriais é um dicionário
        no formato {ip_outra_ponta: linha_serial}. O ip_outra_ponta é o IP do
        host ou roteador que se encontra na outra ponta do enlace, escrito como
        uma string no formato 'x.y.z.w'. A linha_serial é um objeto da classe
        PTY (vide camadafisica.py) ou de outra classe que implemente os métodos
        registrar_recebedor e enviar.
        """
        self.enlaces = {}
        self.callback = None
        # Constrói um Enlace para cada linha serial
        for ip_outra_ponta, linha_serial in linhas_seriais.items():
            enlace = Enlace(linha_serial)
            self.enlaces[ip_outra_ponta] = enlace
            enlace.registrar_recebedor(self._callback)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de enlace
        """
        self.callback = callback

    def enviar(self, datagrama, next_hop):
        """
        Envia datagrama para next_hop, onde next_hop é um endereço IPv4
        fornecido como string (no formato x.y.z.w). A camada de enlace se
        responsabilizará por encontrar em qual enlace se encontra o next_hop.
        """
        # Encontra o Enlace capaz de alcançar next_hop e envia por ele
        self.enlaces[next_hop].enviar(datagrama)

    def _callback(self, datagrama):
        if self.callback:
            self.callback(datagrama)


class Enlace:
    def __init__(self, linha_serial):
        self.linha_serial = linha_serial
        self.linha_serial.registrar_recebedor(self.__raw_recv)
        self.buffer = b''  # Buffer para armazenar dados parciais

    def registrar_recebedor(self, callback):
        self.callback = callback

    def enviar(self, datagrama):
        # Tratar as sequências de escape
        quadro = datagrama.replace(b'\xDB', b'\xDB\xDD').replace(b'\xC0', b'\xDB\xDC')
        # Inserir o byte 0xC0 no início e no fim do quadro
        quadro = b'\xC0' + quadro + b'\xC0'
        # Enviar o quadro pela linha serial
        self.linha_serial.enviar(quadro)

    def __raw_recv(self, dados):
        # Adiciona os dados recebidos ao buffer
        self.buffer += dados

        # Processa o buffer para extrair quadros completos
        while b'\xC0' in self.buffer:
            # Divide o buffer nos dados antes do delimitador e o restante do buffer
            quadro, _, self.buffer = self.buffer.partition(b'\xC0')

            # Ignora datagramas vazios (quadros delimitados por 0xC0 sem dados)
            if len(quadro) == 0:
                continue

            # Tratar as sequências de escape
            try:
                quadro = quadro.replace(b'\xDB\xDC', b'\xC0').replace(b'\xDB\xDD', b'\xDB')
            except Exception as e:
                # Ignora quadro malformado e limpa o buffer
                self.buffer = b''
                return

            # Chama o callback com o datagrama completo e trata excesões
            try:
                if self.callback:
                    self.callback(quadro)
            except Exception as e:
                # Ignora a excesão, mas exibe o rastreamento de erro para depuração
                import traceback
                traceback.print_exc()
                # Limpa o buffer residual
                self.buffer = b''
                return
