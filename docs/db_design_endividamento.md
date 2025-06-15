## Projeto do Banco de Dados para Gerenciamento de Endividamentos

Para implementar a funcionalidade de gerenciamento de endividamentos, será necessário adicionar novas tabelas ao esquema do banco de dados existente, bem como estabelecer relacionamentos com as tabelas `Pessoa` e `Fazenda`.

### 1. Tabela `Endividamento`

Esta tabela armazenará as informações principais de cada endividamento.

| Campo                  | Tipo de Dados | Restrições       | Descrição                                         |
|------------------------|---------------|------------------|---------------------------------------------------|
| `id`                   | INTEGER       | PRIMARY KEY, AUTO_INCREMENT | Identificador único do endividamento.             |
| `banco`                | VARCHAR(255)  | NOT NULL         | Nome do banco onde o endividamento foi contraído. |
| `numero_proposta`      | VARCHAR(255)  | NOT NULL         | Número de identificação da proposta/contrato.     |
| `data_emissao`         | DATE          | NOT NULL         | Data de emissão do endividamento.                 |
| `data_vencimento_final`| DATE          | NOT NULL         | Data do último vencimento do contrato.            |
| `taxa_juros`           | DECIMAL(10,4) | NOT NULL         | Taxa de juros aplicada ao endividamento.          |
| `tipo_taxa_juros`      | VARCHAR(10)   | NOT NULL         | Tipo da taxa de juros (e.g., 'ano', 'mes').       |
| `prazo_carencia`       | INTEGER       | NULLABLE         | Prazo de carência em meses (opcional).            |

### 2. Tabela `Endividamento_Pessoa` (Tabela de Relacionamento Many-to-Many)

Esta tabela fará a ligação entre um endividamento e as pessoas a ele vinculadas.

| Campo                  | Tipo de Dados | Restrições       | Descrição                                         |
|------------------------|---------------|------------------|---------------------------------------------------|
| `endividamento_id`     | INTEGER       | FOREIGN KEY (`Endividamento.id`) | Referência ao ID do endividamento.                |
| `pessoa_id`            | INTEGER       | FOREIGN KEY (`Pessoa.id`)        | Referência ao ID da pessoa.                       |
| `PRIMARY KEY (endividamento_id, pessoa_id)` |

### 3. Tabela `Endividamento_Fazenda` (Tabela de Relacionamento para Objeto do Crédito e Garantias)

Esta tabela permitirá vincular um endividamento a uma ou mais fazendas, especificando a quantidade de hectares e o tipo de vínculo (objeto do crédito ou garantia). Também permitirá um campo de texto livre para descrições adicionais.

| Campo                  | Tipo de Dados | Restrições       | Descrição                                         |
|------------------------|---------------|------------------|---------------------------------------------------|
| `id`                   | INTEGER       | PRIMARY KEY, AUTO_INCREMENT | Identificador único do vínculo.                   |
| `endividamento_id`     | INTEGER       | FOREIGN KEY (`Endividamento.id`), NOT NULL | Referência ao ID do endividamento.                |
| `fazenda_id`           | INTEGER       | FOREIGN KEY (`Fazenda.id`), NULLABLE | Referência ao ID da fazenda (se aplicável).       |
| `hectares`             | DECIMAL(10,2) | NULLABLE         | Quantidade de hectares utilizada (se aplicável).  |
| `tipo`                 | VARCHAR(50)   | NOT NULL         | Tipo de vínculo ('objeto_credito' ou 'garantia'). |
| `descricao`            | TEXT          | NULLABLE         | Descrição livre para o objeto ou garantia.        |

### 4. Tabela `Parcela`

Esta tabela armazenará os detalhes de cada parcela de um endividamento.

| Campo                  | Tipo de Dados | Restrições       | Descrição                                         |
|------------------------|---------------|------------------|---------------------------------------------------|
| `id`                   | INTEGER       | PRIMARY KEY, AUTO_INCREMENT | Identificador único da parcela.                   |
| `endividamento_id`     | INTEGER       | FOREIGN KEY (`Endividamento.id`), NOT NULL | Referência ao ID do endividamento.                |
| `data_vencimento`      | DATE          | NOT NULL         | Data de vencimento da parcela.                    |
| `valor`                | DECIMAL(10,2) | NOT NULL         | Valor da parcela.                                 |

### Relacionamentos

- **`Endividamento` para `Pessoa`:** Relacionamento muitos-para-muitos (`Many-to-Many`) através da tabela associativa `Endividamento_Pessoa`.
- **`Endividamento` para `Fazenda`:** Relacionamento muitos-para-muitos (`Many-to-Many`) através da tabela associativa `Endividamento_Fazenda`, que também discrimina o tipo de vínculo (objeto do crédito ou garantia) e permite descrições livres.
- **`Endividamento` para `Parcela`:** Relacionamento um-para-muitos (`One-to-Many`), onde um endividamento pode ter várias parcelas.

Este design de banco de dados permitirá armazenar todas as informações solicitadas para o gerenciamento de endividamentos, mantendo a flexibilidade para vincular a múltiplas pessoas e fazendas, e detalhar as parcelas.

