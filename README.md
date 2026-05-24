# Piano Fatorado: Analisador Matemático e Musical

O presente repositório contém um script em Python desenvolvido para a análise matemática de estruturas musicais, fundamentando-se na intersecção entre a teoria musical e a teoria dos números. O algoritmo mapeia notas de partituras (MusicXML) para os 88 índices físicos do piano e realiza análises estatísticas baseadas na decomposição em fatores primos de cada tecla.

## O que é

O "Piano Fatorado" é uma ferramenta computacional para extração, conversão e processamento de dados simbólicos musicais. O script lê partituras digitais, extrai as alturas das notas (filtrando pausas e abstraindo acordes para a sua nota principal na métrica adotada) e converte a notação musical tradicional num sistema numérico absoluto baseado no teclado do piano, onde a tecla 1 corresponde à frequência mais grave (Lá0) e a tecla 88 à frequência mais aguda (Dó8). 

## O que se propõe a fazer

O sistema tem como objetivo principal possibilitar o estudo de uma peça musical sob a ótica da "sonificação por fatoração prima" e da estatística matemática. A metodologia aplicada consiste nas seguintes etapas:

1. **Mapeamento Numérico:** Conversão das propriedades de altura (nota e oitava) num índice inteiro de 1 a 88.
2. **Classificação:** Categorização de cada índice/tecla ativado como número primo, composto ou unidade (tecla 1).
3. **Fatoração:** Aplicação do Teorema Fundamental da Aritmética para decompor os índices compostos nos seus fatores primos constituintes.
4. **Análise Estatística:** Cálculo da distribuição de frequências relativas, aferindo a proporção de teclas pares versus ímpares e notas primas versus compostas ao longo da peça.
5. **Mapeamento Cronológico:** Registo sequencial compasso a compasso, documentando a evolução matemática da obra no tempo.

## Entradas de Dados

O algoritmo processa dados de partituras digitais estandardizadas no formato MusicXML. O sistema é compatível com os seguintes formatos de ficheiro:
* Ficheiros MusicXML descompactados (`.musicxml`, `.xml`).
* Ficheiros MusicXML compactados (`.mxl`).

O sistema oferece duas vias de submissão de dados pelo utilizador:
* **Interface de Linha de Comandos (CLI):** O utilizador insere o caminho do ficheiro (ou múltiplos ficheiros) diretamente como argumento durante a invocação do script (ex: `python piano_fatorado.py partitura.mxl`).
* **Interface Gráfica Nativa (GUI):** A execução do script sem argumentos de terminal invoca automaticamente uma caixa de diálogo do sistema (via biblioteca `tkinter`), permitindo a seleção manual do ficheiro.

## OUTPUT

Após o processamento dos dados estruturais, o sistema gera os resultados através de duas vias de saída:
1. **Standard Output:** Exibição imediata do progresso e dos dados processados na consola/terminal.
2. **Relatório Analítico:** Geração de um ficheiro de texto plano (`.txt`), guardado no mesmo diretório do ficheiro de origem, com o sufixo `_piano_fatorado.txt`.

O relatório gerado contém as seguintes secções detalhadas:
* **Resumo Geral:** Contagem absoluta do total de notas processadas e validadas.
* **Extensão (Range):** Identificação das frequências extremas da peça (tecla mais grave e mais aguda) e o cálculo da amplitude total em semitons.
* **Análise Piano Fatorado:** Dados quantitativos e percentuais absolutos referentes à incidência de notas primas e compostas na composição.
* **Paridade:** Distribuição percentual de ocorrências entre teclas de índice numérico par e ímpar.
* **Detalhamento por Tecla:** Uma tabela de frequências que lista cada tecla acionada, a sua designação musical (ex: Fá4), a sua tipologia matemática, a sua fatoração exata e a quantidade de ocorrências na obra.
* **Execução Cronológica:** Um mapeamento temporal organizado por compassos, descrevendo a sequência matemática linear da música à medida que é executada.

## Requisitos do Sistema

O código foi desenvolvido com foco em alta portabilidade e mínimo atrito de configuração. Utiliza exclusivamente bibliotecas da Standard Library do Python (`xml.etree.ElementTree`, `zipfile`, `sys`, `os`, `io`, `datetime`, `collections`, `tkinter`). Não é requerida a instalação de dependências ou pacotes externos via gestores como o pip, bastando uma instalação padrão do interpretador Python 3.x.
