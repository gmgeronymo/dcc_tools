<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" 
		xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
		xmlns:dcc="https://ptb.de/dcc"
		xmlns:si="https://ptb.de/si"
		exclude-result-prefixes="dcc si">
  
  <xsl:output method="html" encoding="utf-8" indent="yes"/>

  <xsl:template match="/">
    <!--
      Indicadores usados na capa e no corpo:
      - $hasCMC: declaração textual do CIPM MRA (mantém compatibilidade com
        certificados antigos e com o statement estruturado basic_isInCMC);
      - $cmcOutsideCount: total de pontos marcados como fora da CMC.
    -->
    <xsl:variable name="hasCMC"
      select="boolean(//dcc:statements/dcc:statement[dcc:declaration/dcc:content[contains(., 'CMC') and contains(., 'MRA')]])"/>
    <xsl:variable name="labHead"
      select="//dcc:respPersons/dcc:respPerson[contains(dcc:role, 'Chefe do Lab')][1]"/>
    <xsl:variable name="executor"
      select="//dcc:respPersons/dcc:respPerson[contains(dcc:role, 'Execut')][1]"/>
    <xsl:variable name="mainSigner"
      select="//dcc:respPersons/dcc:respPerson[dcc:mainSigner='true'][1]"/>
    <xsl:variable name="customerLocation" select="//dcc:customer/dcc:location"/>
    <xsl:variable name="labContact" select="//dcc:calibrationLaboratory/dcc:contact"/>
    <xsl:variable name="resultNodes" select="//dcc:results/dcc:result"/>
    <xsl:variable name="cmcOutsideCount">
      <xsl:variable name="allCmcValues">
        <xsl:for-each select="//dcc:results/dcc:result/dcc:data/dcc:list/dcc:quantity/dcc:measurementMetaData/dcc:metaData[1]">
          <xsl:choose>
            <xsl:when test="dcc:validXMLList">
              <xsl:value-of select="dcc:validXMLList"/>
            </xsl:when>
            <xsl:when test="dcc:valid">
              <xsl:value-of select="dcc:valid"/>
            </xsl:when>
          </xsl:choose>
          <xsl:text> </xsl:text>
        </xsl:for-each>
      </xsl:variable>
      <xsl:call-template name="count-false">
        <xsl:with-param name="text" select="$allCmcValues"/>
      </xsl:call-template>
    </xsl:variable>
    <!-- Nome da coluna de resultados do primeiro mensurando (E.M./V.M.). -->
    <xsl:variable name="firstResultQuantity"
      select="(//dcc:results/dcc:result[1]/dcc:data/dcc:list/dcc:quantity[not(dcc:charsXMLList)])[last()]"/>
    <xsl:variable name="firstResultColumnName"
      select="$firstResultQuantity/dcc:name/dcc:content"/>

    <html>
      <head>
        <meta charset="utf-8"/>
        <title>Certificado de Calibração - <xsl:value-of select="//dcc:uniqueIdentifier"/></title>
        <style>
          /* 1. CONFIGURACOES GERAIS DO DOCUMENTO */
          @page {
            size: A4;
            margin: 1cm 1cm 1cm;
            @bottom-right {
              content: "(Pág. " counter(page) "/" counter(pages) ")";
              font-family: Arial, sans-serif;
              font-size: 8pt;
              font-weight: bold;
            }
            @bottom-left {
              content: "Instituto Nacional de Metrologia, Qualidade e Tecnologia - Inmetro";
              font-family: Arial, sans-serif;
              font-size: 7pt;
              color: #555;
            }
          }

          @page :first {
            margin: 1cm;
            @bottom-right { content: none; }
            @bottom-left { content: none; }
          }

          * { box-sizing: border-box; }

          body {
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            line-height: 1.3;
            color: #000;
            background-color: #525659;
            margin: 0;
            padding: 20px 0;
          }

          /* 2. CABECALHO DA PRIMEIRA PAGINA */
          .cabecalho-rosto {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            min-height: 16mm;
            border-top: 3pt solid #000;
            border-bottom: 3pt solid #000;
            padding: 4px 0;
            font-family: Arial, sans-serif;
            font-size: 8pt;
            text-align: center;
          }
          .cabecalho-rosto-logo { width: 35mm; text-align: left; }
          .cabecalho-rosto-institucional { flex: 1; text-align: center; }
          .cabecalho-rosto-cipm { width: 35mm; text-align: right; }

          /* 3. RODAPE DA PRIMEIRA PAGINA */
          .rodape-rosto {
            width: 100%;
            border-top: 1pt solid #000;
            padding-top: 4px;
            font-family: "Times New Roman", Times, serif;
            font-size: 8pt;
            font-weight: bold;
            line-height: 1.25;
            text-align: center;
            flex-shrink: 0;
          }

          /* 4. CABECALHO DAS PAGINAS SEGUINTES */
          .cabecalho-corpo {
            display: block;
            width: 100%;
            margin: 0 0 15px;
            padding: 0;
            background: #fff;
          }
          .cabecalho-corpo-faixa {
            position: relative;
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            min-height: 12mm;
            border-top: 3pt solid #000;
            border-bottom: 3pt solid #000;
            padding: 4px 0;
          }
          .cabecalho-corpo-logo {
            width: 35mm;
            text-align: left;
            position: relative;
            z-index: 1;
          }
          .cabecalho-corpo-titulo {
            position: absolute;
            left: 0;
            right: 0;
            width: 100%;
            font-family: "Times New Roman", Times, serif;
            font-size: 24pt;
            font-style: italic;
            text-align: center;
            pointer-events: none;
          }
          .cabecalho-corpo-numero {
            margin-top: 3px;
            font-family: "Times New Roman", Times, serif;
            font-size: 14pt;
            font-weight: bold;
            text-decoration: underline;
            text-align: right;
          }
          .cabecalho-corpo-legenda {
            font-family: "Times New Roman", Times, serif;
            font-size: 9pt;
            font-weight: bold;
            text-align: right;
          }

          /* 5. CORPO DA PRIMEIRA PAGINA */
          .corpo-rosto {
            display: flex;
            flex-direction: column;
            flex: 1;
            min-height: 0;
            margin-left: 5mm;
            margin-right: 5mm;
          }
          .pagina-rosto-superior { flex-shrink: 0; }
          .pagina-rosto-inferior { margin-top: auto; flex-shrink: 0; }

          .titulo-certificado {
            font-size: 42pt;
            font-style: italic;
            text-align: center;
            margin: 6px 0 2px;
          }
          .numero-certificado-rosto {
            text-align: right;
            font-size: 14pt;
            font-weight: bold;
            text-decoration: underline;
          }
          .legenda-certificado-rosto {
            text-align: right;
            font-size: 9pt;
            font-weight: bold;
          }

          /* 5.1 QUADROS DAS SECOES DA FOLHA DE ROSTO */
          .secao-quadro {
            position: relative;
            border: 0.5mm solid #b7b7b7;
            padding: 5mm 4mm 3mm;
            margin-top: 7mm;
            box-sizing: border-box;
          }
          .secao-quadro .secao-titulo {
            position: absolute;
            top: -3.5mm;
            left: 4mm;
            margin: 0;
            padding: 0 2mm;
            background-color: #fff;
            border: none;
            font-size: 13pt;
            font-weight: bold;
            font-style: italic;
            line-height: 1.2;
          }
          .grid-campos {
            width: 100%;
            border-collapse: collapse;
            margin-top: 0;
            margin-bottom: 0;
          }
          .grid-campos td {
            padding: 2px 0;
            font-size: 11pt;
            vertical-align: top;
          }
          .grid-campos td.metade { width: 50%; }

          .bloco-assinatura {
            text-align: center;
            margin-bottom: 10px;
            font-size: 11pt;
          }
          .declaracoes-rosto {
            font-family: Arial, sans-serif;
            font-size: 8pt;
            text-align: justify;
            margin-top: 5px;
            line-height: 1.25;
          }
          .declaracoes-rosto p { margin-top: 0; margin-bottom: 4px; }
          .declaracoes-rosto p:last-child { margin-bottom: 0; }

          /* 6. CORPO DAS PAGINAS SEGUINTES */
          .corpo-paginas { margin-left: 5mm; margin-right: 5mm; }
          .corpo-paginas .secao-titulo {
            position: static;
            display: block;
            margin: 26pt 0 13pt;
            padding: 0;
            background-color: transparent;
            border: none;
            font-size: 13pt;
            font-weight: bold;
            font-style: italic;
            line-height: 1.2;
          }
          .texto-bloco {
            font-size: 11pt;
            text-align: justify;
            margin-top: 0;
            margin-bottom: 26px;
          }
          .texto-bloco p { margin: 0 0 8px; }
          .texto-bloco p:last-child { margin-bottom: 0; }
          .lista-metodos { margin: 0; padding-left: 20pt; }
          .lista-metodos li { margin-bottom: 6pt; text-align: justify; }
          .lista-metodos li:last-child { margin-bottom: 0; }

          .dados-tabela {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            margin-bottom: 26px;
          }
          .dados-tabela th,
          .dados-tabela td {
            border: 1px solid #000;
            padding: 5px;
            text-align: center;
            font-size: 11pt;
          }
          .dados-tabela th { font-weight: bold; }
          .dados-tabela .linha-titulo-tabela th {
            text-align: center;
            font-size: 11pt;
            padding: 7px 5px;
            border-top: none !important;
            border-left: none !important;
            border-right: none !important;
          }
          .dados-tabela td.cmc-fora { font-weight: bold; }

          /* 6.1 AVISOS E OBSERVACOES */
          .obs { margin: 8px 0; font-size: 10px; line-height: 1.2; }

          /* 7. ESTRUTURA FISICA DAS PAGINAS NA TELA */
          .pagina-rosto-container {
            display: flex;
            flex-direction: column;
            width: 21cm;
            height: 29.7cm;
            margin: 0 auto 20px;
            padding: 1cm;
            background-color: #fff;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
            box-sizing: border-box;
            page-break-after: always;
            break-after: page;
            overflow: hidden;
          }
          .pagina-corpo {
            width: 21cm;
            min-height: 29.7cm;
            margin: 0 auto 20px;
            padding: 1cm;
            background-color: #fff;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
            box-sizing: border-box;
            page-break-after: auto;
            break-after: auto;
          }
          .estrutura-paginas {
            display: table;
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            table-layout: fixed;
          }
          .estrutura-paginas thead { display: table-header-group; }
          .estrutura-paginas tbody { display: table-row-group; }
          .estrutura-paginas > thead > tr > td,
          .estrutura-paginas > tbody > tr > td {
            border: none;
            padding: 0;
            vertical-align: top;
          }

          /* 8. BARRA DE ACOES */
          .no-print {
            position: sticky;
            top: 0;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            padding: 10px 20px;
            text-align: right;
            z-index: 9999;
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 10px;
          }
          .no-print span {
            font-family: sans-serif;
            font-size: 13px;
            color: #6c757d;
            margin-right: auto;
          }
          .no-print button {
            background-color: #0d6efd;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            cursor: pointer;
          }

          /* 9. IMPRESSAO E GERACAO DO PDF */
          @media print {
            body {
              background-color: #fff !important;
              margin: 0 !important;
              padding: 0 !important;
            }
            .no-print { display: none !important; }

            .pagina-rosto-container {
              width: 100% !important;
              height: 27.7cm !important;
              max-height: 27.7cm !important;
              margin: 0 !important;
              padding: 0 !important;
              box-shadow: none !important;
              position: relative !important;
              z-index: 20 !important;
              background-color: #fff !important;
              page-break-after: always;
              break-after: page;
              overflow: hidden;
            }
            .corpo-rosto {
              display: flex !important;
              flex-direction: column !important;
              flex: 1 !important;
              min-height: 0 !important;
              margin-left: 5mm !important;
              margin-right: 5mm !important;
            }
            .pagina-corpo {
              width: 100% !important;
              min-height: 0 !important;
              margin: 0 !important;
              padding: 0 !important;
              box-shadow: none !important;
              background-color: #fff !important;
              page-break-after: auto !important;
              break-after: auto !important;
            }
            .estrutura-paginas {
              display: table !important;
              width: 100% !important;
              border-collapse: collapse !important;
              border-spacing: 0 !important;
              table-layout: fixed !important;
            }
            .estrutura-paginas thead { display: table-header-group !important; }
            .estrutura-paginas tbody { display: table-row-group !important; }
            .estrutura-paginas tr {
              page-break-inside: auto !important;
              break-inside: auto !important;
            }
            .estrutura-paginas th,
            .estrutura-paginas td {
              border: none !important;
              padding: 0 !important;
              vertical-align: top !important;
            }

            .cabecalho-corpo {
              display: block !important;
              position: static !important;
              width: 100% !important;
              margin: 0 0 15px !important;
              padding: 0 !important;
              background: #fff !important;
            }
            .cabecalho-corpo-faixa {
              position: relative !important;
              display: flex !important;
              justify-content: space-between !important;
              align-items: center !important;
              width: 100% !important;
              min-height: 12mm !important;
              border-top: 3pt solid #000 !important;
              border-bottom: 3pt solid #000 !important;
              padding: 4px 0 !important;
            }
            .cabecalho-corpo-logo { position: relative !important; z-index: 1 !important; }
            .cabecalho-corpo-titulo {
              position: absolute !important;
              left: 0 !important;
              right: 0 !important;
              width: 100% !important;
              font-family: "Times New Roman", Times, serif !important;
              font-size: 24pt !important;
              font-style: italic !important;
              text-align: center !important;
              pointer-events: none !important;
            }
            .cabecalho-corpo-numero {
              margin-top: 3px !important;
              font-family: "Times New Roman", Times, serif !important;
              font-size: 14pt !important;
              font-weight: bold !important;
              text-decoration: underline !important;
              text-align: right !important;
            }
            .cabecalho-corpo-legenda {
              font-family: "Times New Roman", Times, serif !important;
              font-size: 9pt !important;
              font-weight: bold !important;
              text-align: right !important;
            }

            .corpo-paginas {
              margin-left: 5mm !important;
              margin-right: 5mm !important;
            }

            .dados-tabela {
              display: table !important;
              width: 100% !important;
              border-collapse: collapse !important;
              border-spacing: 0 !important;
              table-layout: auto !important;
            }
            .dados-tabela thead { display: table-header-group !important; }
            .dados-tabela tbody { display: table-row-group !important; }
            .dados-tabela tr {
              page-break-inside: avoid;
              break-inside: avoid;
            }
            .dados-tabela th,
            .dados-tabela td {
              border: 1px solid #000 !important;
              padding: 5px !important;
              text-align: center !important;
              font-size: 11pt !important;
            }
            .dados-tabela .linha-titulo-tabela th {
              text-align: center;
              font-size: 11pt;
              padding: 7px 5px;
              border-top: none !important;
              border-left: none !important;
              border-right: none !important;
            }

            .titulo-tabela {
              page-break-after: avoid;
              break-after: avoid;
            }
            .obs {
              page-break-inside: avoid;
              break-inside: avoid;
            }
            .secao-quadro {
              page-break-inside: avoid;
              break-inside: avoid;
            }
          }
        </style>
      </head>
      <body>

        <div class="no-print">
          <span>Visualização do Certificado de Calibração (Norma NIE-Dimci-014)</span>
          <button onclick="window.print()">Imprimir / Salvar em PDF</button>
        </div>

        <!-- PAGINA 1 - FOLHA DE ROSTO -->
        <div class="pagina-rosto-container">

          <header class="cabecalho-rosto">
            <div class="cabecalho-rosto-logo">
              <img src="static/examples/xslt/logo_inmetro.png" alt="Logo Inmetro" style="max-height: 12mm; max-width: 32mm;"/>
            </div>
            <div class="cabecalho-rosto-institucional">
              Serviço Público Federal<br/>
              Ministério do Desenvolvimento, Indústria, Comércio e Serviços (MDIC)<br/>
              Instituto Nacional de Metrologia, Qualidade e Tecnologia (Inmetro)
            </div>
            <div class="cabecalho-rosto-cipm">
              <xsl:if test="$hasCMC">
                <img src="static/examples/xslt/logo_mra.png" alt="Logo CIPM MRA" style="height: 14.7mm; width: 30.5mm;"/>
              </xsl:if>
            </div>
          </header>

          <main class="corpo-rosto">
            <div class="pagina-rosto-superior">

              <div class="titulo-certificado">Certificado de Calibração</div>

              <div class="numero-certificado-rosto">
                <xsl:value-of select="//dcc:uniqueIdentifier"/>
              </div>
              <div class="legenda-certificado-rosto">Número do Certificado</div>

              <!-- 1. Cliente -->
              <div class="secao-quadro">
                <div class="secao-titulo">Cliente</div>
                <div>
                  <strong>Nome: </strong> <xsl:value-of select="//dcc:customer/dcc:name/dcc:content"/>
                </div>
                <div>
                  <strong>Endereço: </strong>
                  <xsl:value-of select="$customerLocation/dcc:street"/><xsl:text>, </xsl:text>
                  <xsl:value-of select="$customerLocation/dcc:streetNo"/><xsl:text> - </xsl:text>
                  <xsl:value-of select="$customerLocation/dcc:city"/><xsl:text> / </xsl:text>
                  <xsl:value-of select="$customerLocation/dcc:state"/><xsl:text> - CEP: </xsl:text>
                  <xsl:value-of select="$customerLocation/dcc:postCode"/>
                </div>
              </div>

              <!-- 2. Identificacao do Item -->
              <div class="secao-quadro">
                <div class="secao-titulo">Identificação do Item</div>
                <table class="grid-campos">
                  <tr>
                    <td colspan="2">
                      <strong>Item: </strong> <xsl:value-of select="//dcc:item/dcc:name/dcc:content"/>
                    </td>
                  </tr>
                  <tr>
                    <td class="metade">
                      <strong>Fabricante: </strong> <xsl:value-of select="//dcc:item/dcc:manufacturer/dcc:name/dcc:content"/>
                    </td>
                    <td class="metade">
                      <strong>Modelo/Tipo: </strong> <xsl:value-of select="//dcc:item/dcc:model"/>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <strong>Número de Série: </strong> <xsl:value-of select="//dcc:item/dcc:identifications/dcc:identification[dcc:issuer='manufacturer']/dcc:value"/>
                    </td>
                    <td>
                      <strong>Código de Identificação: </strong> <xsl:value-of select="//dcc:item/dcc:identifications/dcc:identification[dcc:issuer='customer']/dcc:value"/>
                    </td>
                  </tr>
                </table>
              </div>

              <!-- 3. Laboratorio Executor -->
              <div class="secao-quadro">
                <div class="secao-titulo">Laboratório Executor</div>
                <table class="grid-campos">
                  <tr>
                    <td colspan="2">
                      <strong>Laboratório Responsável: </strong>
                      <xsl:value-of select="$labContact/dcc:name/dcc:content"/>
                    </td>
                  </tr>
                  <tr>
                    <td colspan="2">
                      <strong>Técnico Executor: </strong>
                      <xsl:choose>
                        <xsl:when test="$executor">
                          <xsl:value-of select="$executor/dcc:person/dcc:name/dcc:content"/>
                        </xsl:when>
                        <xsl:otherwise>Não informado</xsl:otherwise>
                      </xsl:choose>
                    </td>
                  </tr>
                  <tr>
                    <td colspan="2">
                      <strong>Responsável Técnico: </strong>
                      <xsl:choose>
                        <xsl:when test="$labHead">
                          <xsl:value-of select="$labHead/dcc:person/dcc:name/dcc:content"/>
                          <xsl:text> / </xsl:text>
                          <xsl:value-of select="$labHead/dcc:role"/>
                        </xsl:when>
                        <xsl:otherwise>Não informado</xsl:otherwise>
                      </xsl:choose>
                    </td>
                  </tr>
                  <tr>
                    <td colspan="2">
                      <strong>Data da Calibração: </strong>
                      <xsl:call-template name="format-date">
                        <xsl:with-param name="date" select="//dcc:beginPerformanceDate"/>
                      </xsl:call-template>
                    </td>
                  </tr>
                </table>
              </div>

              <!-- 4. Informacoes Administrativas -->
              <div class="secao-quadro">
                <div class="secao-titulo">Informações Administrativas</div>
                <table class="grid-campos">
                  <tr>
                    <td colspan="2">
                      <strong>Processo Inmetro: </strong>
                      <xsl:choose>
                        <xsl:when test="//dcc:coreData/dcc:identifications/dcc:identification[dcc:issuer='calibrationLaboratory']/dcc:value">
                          <xsl:value-of select="//dcc:coreData/dcc:identifications/dcc:identification[dcc:issuer='calibrationLaboratory']/dcc:value"/>
                        </xsl:when>
                        <xsl:otherwise>
                          <xsl:value-of select="//dcc:coreData/dcc:identifications/dcc:identification/dcc:value"/>
                        </xsl:otherwise>
                      </xsl:choose>
                    </td>
                  </tr>
                  <tr>
                    <td colspan="2">
                      <strong>Data de Emissão: </strong>
                      <xsl:variable name="issueStatement"
                        select="//dcc:statements/dcc:statement[dcc:name/dcc:content='Data de Emissão']/dcc:description/dcc:content"/>
                      <xsl:variable name="issueDate" select="//dcc:coreData/dcc:issueDate"/>
                      <xsl:choose>
                        <xsl:when test="normalize-space($issueStatement) != ''">
                          <xsl:value-of select="$issueStatement"/>
                        </xsl:when>
                        <xsl:when test="normalize-space($issueDate) != ''">
                          <xsl:call-template name="format-date">
                            <xsl:with-param name="date" select="$issueDate"/>
                          </xsl:call-template>
                        </xsl:when>
                        <xsl:otherwise>Ver data da assinatura eletrônica presente no certificado</xsl:otherwise>
                      </xsl:choose>
                    </td>
                  </tr>
                </table>
              </div>

            </div>

            <!-- ASSINATURA E DECLARACOES -->
            <div class="pagina-rosto-inferior">

              <div class="bloco-assinatura">
                <strong style="font-size: 11pt; font-style: italic;">
                  <xsl:choose>
                    <xsl:when test="$mainSigner">
                      <xsl:value-of select="$mainSigner/dcc:person/dcc:name/dcc:content"/>
                    </xsl:when>
                    <xsl:otherwise>
                      <xsl:value-of select="//dcc:respPersons/dcc:respPerson[1]/dcc:person/dcc:name/dcc:content"/>
                    </xsl:otherwise>
                  </xsl:choose>
                </strong>
                <br/>
                <span style="font-size: 9pt; font-weight: bold;">
                  <xsl:choose>
                    <xsl:when test="$mainSigner">
                      <xsl:value-of select="$mainSigner/dcc:role"/>
                    </xsl:when>
                    <xsl:otherwise>
                      <xsl:value-of select="//dcc:respPersons/dcc:respPerson[1]/dcc:role"/>
                    </xsl:otherwise>
                  </xsl:choose>
                </span>
              </div>

              <div class="declaracoes-rosto">
                <xsl:if test="$hasCMC">
                  <xsl:variable name="cmcDeclaration"
                    select="//dcc:statements/dcc:statement[dcc:declaration/dcc:content[contains(., 'CMC') and contains(., 'MRA')]]/dcc:declaration/dcc:content"/>
                  <xsl:if test="normalize-space($cmcDeclaration) != ''">
                    <p><xsl:value-of select="$cmcDeclaration"/></p>
                  </xsl:if>
                </xsl:if>
                <xsl:variable name="normDeclaration"
                  select="//dcc:statements/dcc:statement[dcc:norm]/dcc:declaration/dcc:content"/>
                <xsl:if test="normalize-space($normDeclaration) != ''">
                  <p><xsl:value-of select="$normDeclaration"/></p>
                </xsl:if>
              </div>

            </div>
          </main>

          <footer class="rodape-rosto">
            Inmetro - Av. Nossa Senhora das Graças, 50 - Xerém - Duque de Caxias - RJ - Brasil - CEP: 25250-020<br/>
            Dimci - Tel: <xsl:value-of select="$labContact/dcc:phone"/> - e-mail: <xsl:value-of select="$labContact/dcc:eMail"/>
          </footer>

        </div>

        <!-- PAGINAS SEGUINTES - CORPO DO CERTIFICADO -->
        <div class="pagina-corpo">
          <table class="estrutura-paginas">
            <thead>
              <tr>
                <td>
                  <header class="cabecalho-corpo">
                    <div class="cabecalho-corpo-faixa">
                      <div class="cabecalho-corpo-logo">
                        <img src="static/examples/xslt/logo_inmetro.png" alt="Logo Inmetro" style="max-height: 10mm; max-width: 28mm;"/>
                      </div>
                      <div class="cabecalho-corpo-titulo">Certificado de Calibração</div>
                    </div>
                    <div class="cabecalho-corpo-numero">
                      <xsl:value-of select="//dcc:uniqueIdentifier"/>
                    </div>
                    <div class="cabecalho-corpo-legenda">Número do Certificado</div>
                  </header>
                </td>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <main class="corpo-paginas">

                    <!-- Caracteristicas do Item e valor nominal estruturado -->
                    <xsl:variable name="itemCharacteristics"
                      select="//dcc:statements/dcc:statement[dcc:name/dcc:content='Características do Item']/dcc:description/dcc:content"/>
                    <xsl:variable name="nominalValues"
                      select="//dcc:item/dcc:itemQuantities/dcc:itemQuantity[contains(concat(' ', @refType, ' '), ' basic_nominalValue ')]"/>
                    <xsl:if test="normalize-space($itemCharacteristics) != '' or $nominalValues">
                      <div class="secao-titulo">Características do Item</div>
                      <xsl:if test="normalize-space($itemCharacteristics) != ''">
                        <div class="texto-bloco">
                          <strong>Funções / Descrição: </strong> <xsl:value-of select="$itemCharacteristics"/>
                        </div>
                      </xsl:if>
                      <xsl:if test="$nominalValues">
                        <div class="texto-bloco">
                          <xsl:for-each select="$nominalValues">
                            <div>
                              <strong>
                                <xsl:choose>
                                  <xsl:when test="normalize-space(dcc:name/dcc:content) != ''">
                                    <xsl:value-of select="dcc:name/dcc:content"/>
                                  </xsl:when>
                                  <xsl:otherwise>Valor nominal</xsl:otherwise>
                                </xsl:choose>
                                <xsl:text>: </xsl:text>
                              </strong>
                              <xsl:choose>
                                <xsl:when test="si:real">
                                  <xsl:call-template name="format-number-comma">
                                    <xsl:with-param name="number" select="si:real/si:value"/>
                                  </xsl:call-template>
                                  <xsl:text> </xsl:text>
                                  <xsl:call-template name="format-unit">
                                    <xsl:with-param name="unit" select="si:real/si:unit"/>
                                  </xsl:call-template>
                                </xsl:when>
                                <xsl:when test="si:realListXMLList">
                                  <xsl:value-of select="normalize-space(si:realListXMLList/si:valueXMLList)"/>
                                  <xsl:text> </xsl:text>
                                  <xsl:call-template name="format-unit">
                                    <xsl:with-param name="unit" select="si:realListXMLList/si:unitXMLList"/>
                                  </xsl:call-template>
                                </xsl:when>
                              </xsl:choose>
                            </div>
                            <xsl:if test="normalize-space(dcc:description/dcc:content) != ''">
                              <div class="obs">
                                <xsl:value-of select="dcc:description/dcc:content"/>
                              </div>
                            </xsl:if>
                          </xsl:for-each>
                        </div>
                      </xsl:if>
                    </xsl:if>

                    <!-- Rastreabilidade -->
                    <div class="secao-titulo">Rastreabilidade</div>
                    <div class="texto-bloco">
                      <xsl:choose>
                        <xsl:when test="normalize-space(//dcc:measuringEquipments/dcc:name/dcc:content) != ''">
                          <xsl:value-of select="//dcc:measuringEquipments/dcc:name/dcc:content"/>
                        </xsl:when>
                        <xsl:otherwise>
                          Os resultados da calibração são rastreados ao Sistema Internacional de Unidades (SI), por intermédio dos padrões metrológicos nacionais. As medições realizadas estão referenciadas aos padrões relacionados na Tabela abaixo.
                        </xsl:otherwise>
                      </xsl:choose>
                    </div>

                    <xsl:if test="//dcc:measuringEquipments/dcc:measuringEquipment">
                      <table class="dados-tabela">
                        <thead>
                          <tr class="linha-titulo-tabela">
                            <th colspan="4">TABELA 1 - Padrões Utilizados</th>
                          </tr>
                          <tr>
                            <th>Padrão</th>
                            <th>Identificação</th>
                            <th>Certificado</th>
                            <th>Origem</th>
                          </tr>
                        </thead>
                        <tbody>
                          <xsl:for-each select="//dcc:measuringEquipments/dcc:measuringEquipment">
                            <tr>
                              <td><xsl:value-of select="dcc:name/dcc:content"/></td>
                              <td><xsl:value-of select="dcc:identifications/dcc:identification/dcc:value"/></td>
                              <td><xsl:value-of select="dcc:certificate/dcc:referralID"/></td>
                              <td><xsl:value-of select="dcc:certificate/dcc:referral/dcc:content"/></td>
                            </tr>
                          </xsl:for-each>
                        </tbody>
                      </table>
                    </xsl:if>

                    <!-- Metodo de Medicao -->
                    <div class="secao-titulo">Método de Medição</div>
                    <div class="texto-bloco">
                      <xsl:choose>
                        <xsl:when test="//dcc:usedMethods/dcc:usedMethod[dcc:name/dcc:content='Método de Medição']">
                          <p>O instrumento foi calibrado nas grandezas solicitadas utilizando-se os seguintes métodos:</p>
                          <ul class="lista-metodos">
                            <xsl:for-each select="//dcc:usedMethods/dcc:usedMethod[dcc:name/dcc:content='Método de Medição']">
                              <li><xsl:value-of select="dcc:description/dcc:content"/></li>
                            </xsl:for-each>
                          </ul>
                        </xsl:when>
                        <xsl:otherwise>
                          <p>Métodos de medição não informados.</p>
                        </xsl:otherwise>
                      </xsl:choose>
                    </div>

                    <!-- Informacoes Pertinentes -->
                    <div class="secao-titulo">Informações Pertinentes às Atividades Realizadas</div>
                    <div class="texto-bloco">
                      <xsl:variable name="environmentConditions"
                        select="//dcc:influenceConditions/dcc:influenceCondition[contains(@refType, 'temperature') or contains(@refType, 'humidity') or contains(dcc:name/dcc:content, 'Temperatura') or contains(dcc:name/dcc:content, 'Umidade')]"/>
                      <xsl:variable name="otherConditions"
                        select="//dcc:influenceConditions/dcc:influenceCondition[not(contains(@refType, 'temperature') or contains(@refType, 'humidity') or contains(dcc:name/dcc:content, 'Temperatura') or contains(dcc:name/dcc:content, 'Umidade'))]"/>

                      <xsl:if test="$environmentConditions">
                        Condições ambientais:
                        <div style="margin-left: 20pt;">
                          <xsl:for-each select="$environmentConditions">
                            <xsl:call-template name="render-influence-condition">
                              <xsl:with-param name="condition" select="."/>
                            </xsl:call-template>
                          </xsl:for-each>
                        </div>
                      </xsl:if>

                      <xsl:if test="$otherConditions">
                        <div style="margin-top: 8px;">Configurações do equipamento:</div>
                        <div style="margin-left: 20pt;">
                          <xsl:for-each select="$otherConditions">
                            <xsl:call-template name="render-influence-condition">
                              <xsl:with-param name="condition" select="."/>
                            </xsl:call-template>
                          </xsl:for-each>
                        </div>
                      </xsl:if>

                      <xsl:if test="not($environmentConditions) and not($otherConditions)">
                        <p>Informações não disponíveis.</p>
                      </xsl:if>
                    </div>

                    <!-- Resultados -->
                    <div class="secao-titulo">Resultados e Declaração da Incerteza de Medição</div>
                    <div class="texto-bloco">
                      <xsl:if test="$firstResultColumnName = 'E.M.'">
                        <p>Os resultados da calibração estão contidos nas tabelas a seguir, sendo V.R. valores de referência e E.M. o erro de medição do instrumento sob calibração encontrado, correspondente à média de, pelo menos, 3 medições por ponto.</p>
                      </xsl:if>
                      <xsl:if test="$firstResultColumnName = 'V.M.'">
                        <p>Os resultados da calibração estão contidos nas tabelas a seguir, sendo V.N. os valores nominais indicados no instrumento sob calibração e V.M. os valores medidos pelos padrões do laboratório, correspondentes à média de, pelo menos, 3 medições por ponto.</p>
                      </xsl:if>
                      <xsl:variable name="uncertaintyMethod"
                        select="//dcc:usedMethods/dcc:usedMethod[dcc:name/dcc:content='Declaração da Incerteza de Medição']/dcc:description/dcc:content"/>
                      <xsl:if test="normalize-space($uncertaintyMethod) != ''">
                        <p><xsl:value-of select="$uncertaintyMethod"/></p>
                      </xsl:if>
                    </div>

                    <xsl:for-each select="$resultNodes">
                      <xsl:variable name="resultIndex" select="position()"/>
                      <xsl:variable name="resultName" select="dcc:name/dcc:content"/>
                      <xsl:variable name="quantities" select="dcc:data/dcc:list/dcc:quantity"/>
                      <xsl:variable name="cmcValues">
                        <xsl:for-each select="dcc:data/dcc:list/dcc:quantity/dcc:measurementMetaData/dcc:metaData[1]">
                          <xsl:choose>
                            <xsl:when test="dcc:validXMLList">
                              <xsl:value-of select="normalize-space(dcc:validXMLList)"/>
                            </xsl:when>
                            <xsl:when test="dcc:valid">
                              <xsl:value-of select="normalize-space(dcc:valid)"/>
                            </xsl:when>
                          </xsl:choose>
                        </xsl:for-each>
                      </xsl:variable>
                      <xsl:variable name="hasCmc" select="normalize-space($cmcValues) != ''"/>
                      <xsl:variable name="uncertaintyColumns"
                        select="count($quantities[si:realListXMLList/si:measurementUncertaintyUnivariateXMLList or si:realListXMLList/si:expandedUncXMLList])"/>
                      <xsl:variable name="totalColumns"
                        select="count($quantities) + 2 * $uncertaintyColumns + number($hasCmc)"/>

                      <table class="dados-tabela">
                        <thead>
                          <tr class="linha-titulo-tabela">
                            <th colspan="{$totalColumns}">
                              TABELA <xsl:value-of select="$resultIndex + 1"/> - <xsl:value-of select="$resultName"/>
                            </th>
                          </tr>
                          <tr>
                            <xsl:for-each select="$quantities">
                              <xsl:variable name="unit" select="si:realListXMLList/si:unitXMLList"/>
                              <xsl:variable name="hasUncertainty"
                                select="si:realListXMLList/si:measurementUncertaintyUnivariateXMLList | si:realListXMLList/si:expandedUncXMLList"/>
                              <th>
                                <xsl:value-of select="dcc:name/dcc:content"/>
                                <xsl:if test="$unit != ''">
                                  <br/>(<xsl:call-template name="format-unit">
                                    <xsl:with-param name="unit" select="$unit"/>
                                  </xsl:call-template>)
                                </xsl:if>
                              </th>
                              <xsl:if test="$hasUncertainty">
                                <th>U</th>
                                <th>k</th>
                              </xsl:if>
                            </xsl:for-each>
                            <xsl:if test="$hasCmc">
                              <th>CMC</th>
                            </xsl:if>
                          </tr>
                        </thead>
                        <tbody>
                          <xsl:call-template name="generate-result-rows">
                            <xsl:with-param name="quantities" select="$quantities"/>
                            <xsl:with-param name="cmcValues" select="$cmcValues"/>
                            <xsl:with-param name="hasCmc" select="$hasCmc"/>
                          </xsl:call-template>
                        </tbody>
                      </table>
                    </xsl:for-each>

                    <!-- Observacoes do certificado + observacao sobre a CMC -->
                    <xsl:variable name="observacaoStatementCount"
                      select="count(//dcc:statements/dcc:statement[contains(dcc:name/dcc:content, 'Observação')])"/>
                    <xsl:if test="$observacaoStatementCount &gt; 0 or $cmcOutsideCount &gt; 0">
                      <div class="secao-observacoes">
                        <div class="secao-titulo">Observações</div>
                        <xsl:for-each select="//dcc:statements/dcc:statement[contains(dcc:name/dcc:content, 'Observação')]">
                          <div class="obs">
                            <strong>Obs. <xsl:value-of select="position()"/>: </strong>
                            <xsl:choose>
                              <xsl:when test="dcc:description">
                                <xsl:value-of select="dcc:description/dcc:content"/>
                              </xsl:when>
                              <xsl:when test="dcc:declaration">
                                <xsl:value-of select="dcc:declaration/dcc:content"/>
                              </xsl:when>
                            </xsl:choose>
                          </div>
                        </xsl:for-each>
                        <xsl:if test="$cmcOutsideCount &gt; 0">
                          <div class="obs">
                            <strong>Obs. <xsl:value-of select="$observacaoStatementCount + 1"/>: </strong>
                            <xsl:choose>
                              <xsl:when test="$cmcOutsideCount = 1">
                                O ponto marcado com Não na coluna CMC não está coberto pela Capacidade de Medição e Calibração (CMC) do laboratório no âmbito do CIPM MRA, embora a rastreabilidade esteja garantida da mesma forma que sustenta a dos demais pontos.
                              </xsl:when>
                              <xsl:otherwise>
                                Os pontos marcados com Não na coluna CMC não estão cobertos pela Capacidade de Medição e Calibração (CMC) do laboratório no âmbito do CIPM MRA, embora a rastreabilidade esteja garantida da mesma forma que sustenta a dos demais pontos.
                              </xsl:otherwise>
                            </xsl:choose>
                          </div>
                        </xsl:if>
                      </div>
                    </xsl:if>

                  </main>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </body>
    </html>
  </xsl:template>

  <!-- =====================================================================
       Formatacao de datas (ISO AAAA-MM-DD -> DD/MM/AAAA)
       ===================================================================== -->
  <xsl:template name="format-date">
    <xsl:param name="date"/>
    <xsl:choose>
      <xsl:when test="string-length(normalize-space($date)) &gt;= 10">
        <xsl:value-of select="substring(normalize-space($date), 9, 2)"/>/<xsl:value-of select="substring(normalize-space($date), 6, 2)"/>/<xsl:value-of select="substring(normalize-space($date), 1, 4)"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="normalize-space($date)"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- =====================================================================
       Renderiza uma condicao de influencia (temperatura, umidade,
       configuracao etc.), aceitando valor unico, faixa ou texto.
       ===================================================================== -->
  <xsl:template name="render-influence-condition">
    <xsl:param name="condition"/>

    <xsl:variable name="conditionName" select="$condition/dcc:name/dcc:content"/>
    <xsl:variable name="unit" select="$condition/dcc:data/dcc:quantity[1]/si:real/si:unit"/>
    <xsl:variable name="uncertainty"
      select="$condition/dcc:data/dcc:quantity[1]/si:real/si:measurementUncertaintyUnivariate/si:expandedMU/si:valueExpandedMU | $condition/dcc:data/dcc:quantity[1]/si:real/si:expandedUnc/si:uncertainty"/>
    <xsl:variable name="quantityCount" select="count($condition/dcc:data/dcc:quantity)"/>
    <xsl:variable name="hasRefTypeMin" select="boolean($condition/dcc:data/dcc:quantity[@refType='math_minimum'])"/>
    <xsl:variable name="hasRefTypeMax" select="boolean($condition/dcc:data/dcc:quantity[@refType='math_maximum'])"/>
    <xsl:variable name="hasRange" select="boolean($hasRefTypeMin or $hasRefTypeMax or $quantityCount &gt; 1)"/>
    <xsl:variable name="minValue">
      <xsl:choose>
        <xsl:when test="$hasRefTypeMin">
          <xsl:value-of select="$condition/dcc:data/dcc:quantity[@refType='math_minimum']/si:real/si:value"/>
        </xsl:when>
        <xsl:when test="$quantityCount &gt; 1">
          <xsl:variable name="v1" select="$condition/dcc:data/dcc:quantity[1]/si:real/si:value"/>
          <xsl:variable name="v2" select="$condition/dcc:data/dcc:quantity[2]/si:real/si:value"/>
          <xsl:choose>
            <xsl:when test="$v1 &lt;= $v2"><xsl:value-of select="$v1"/></xsl:when>
            <xsl:otherwise><xsl:value-of select="$v2"/></xsl:otherwise>
          </xsl:choose>
        </xsl:when>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="maxValue">
      <xsl:choose>
        <xsl:when test="$hasRefTypeMax">
          <xsl:value-of select="$condition/dcc:data/dcc:quantity[@refType='math_maximum']/si:real/si:value"/>
        </xsl:when>
        <xsl:when test="$quantityCount &gt; 1">
          <xsl:variable name="v1" select="$condition/dcc:data/dcc:quantity[1]/si:real/si:value"/>
          <xsl:variable name="v2" select="$condition/dcc:data/dcc:quantity[2]/si:real/si:value"/>
          <xsl:choose>
            <xsl:when test="$v1 &gt;= $v2"><xsl:value-of select="$v1"/></xsl:when>
            <xsl:otherwise><xsl:value-of select="$v2"/></xsl:otherwise>
          </xsl:choose>
        </xsl:when>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="singleValue" select="$condition/dcc:data/dcc:quantity[1]/si:real/si:value[not(../../@refType)]"/>

    <xsl:choose>
      <xsl:when test="$condition/dcc:data/dcc:text">
        <strong><xsl:value-of select="$conditionName"/>:</strong>
        <xsl:text> </xsl:text>
        <xsl:value-of select="$condition/dcc:data/dcc:text/dcc:content"/>
        <br/>
      </xsl:when>
      <xsl:when test="$hasRange and $minValue and $maxValue">
        <strong><xsl:value-of select="$conditionName"/>:</strong>
        <xsl:text> </xsl:text>
        <xsl:call-template name="format-number-comma">
          <xsl:with-param name="number" select="$minValue"/>
        </xsl:call-template>
        <xsl:if test="$uncertainty">
          <xsl:text> ± </xsl:text>
          <xsl:call-template name="format-number-comma">
            <xsl:with-param name="number" select="$uncertainty"/>
          </xsl:call-template>
        </xsl:if>
        <xsl:text> </xsl:text>
        <xsl:call-template name="format-unit">
          <xsl:with-param name="unit" select="$unit"/>
        </xsl:call-template>
        <xsl:text> a </xsl:text>
        <xsl:call-template name="format-number-comma">
          <xsl:with-param name="number" select="$maxValue"/>
        </xsl:call-template>
        <xsl:if test="$uncertainty">
          <xsl:text> ± </xsl:text>
          <xsl:call-template name="format-number-comma">
            <xsl:with-param name="number" select="$uncertainty"/>
          </xsl:call-template>
        </xsl:if>
        <xsl:text> </xsl:text>
        <xsl:call-template name="format-unit">
          <xsl:with-param name="unit" select="$unit"/>
        </xsl:call-template>
        <xsl:if test="contains($conditionName, 'Umidade') or contains($conditionName, 'umidade')">
          <xsl:text> ur</xsl:text>
        </xsl:if>
        <br/>
      </xsl:when>
      <xsl:when test="$singleValue">
        <strong><xsl:value-of select="$conditionName"/>:</strong>
        <xsl:text> </xsl:text>
        <xsl:choose>
          <xsl:when test="contains($conditionName, 'Umidade')">
            <xsl:call-template name="format-number-comma">
              <xsl:with-param name="number" select="$singleValue"/>
            </xsl:call-template>
            <xsl:if test="$uncertainty">
              <xsl:text> ± </xsl:text>
              <xsl:call-template name="format-number-comma">
                <xsl:with-param name="number" select="$uncertainty"/>
              </xsl:call-template>
            </xsl:if>
            <xsl:text> </xsl:text>
            <xsl:call-template name="format-unit">
              <xsl:with-param name="unit" select="$unit"/>
            </xsl:call-template>
            <xsl:text> ur</xsl:text>
          </xsl:when>
          <xsl:otherwise>
            <xsl:call-template name="format-number-comma">
              <xsl:with-param name="number" select="$singleValue"/>
            </xsl:call-template>
            <xsl:text> </xsl:text>
            <xsl:call-template name="format-unit">
              <xsl:with-param name="unit" select="$unit"/>
            </xsl:call-template>
            <xsl:if test="$uncertainty">
              <xsl:text> ± </xsl:text>
              <xsl:call-template name="format-number-comma">
                <xsl:with-param name="number" select="$uncertainty"/>
              </xsl:call-template>
            </xsl:if>
          </xsl:otherwise>
        </xsl:choose>
        <br/>
      </xsl:when>
      <xsl:otherwise>
        <strong><xsl:value-of select="$conditionName"/>:</strong>
        <xsl:text> [Dados não disponíveis]</xsl:text>
        <br/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- =====================================================================
       Conta quantos valores "false" existem em uma lista de booleanos
       separada por espacos. Usa aritmetica sobre o comprimento da string
       para evitar recursao profunda em certificados com muitos pontos.

       - true/false: cada "true" tem 4 caracteres e cada "false" tem 5.
         Com n tokens e L caracteres (sem espacos), f = L - 4*n.
       - 1/0 (xs:boolean alternativo): conta os "0".
       ===================================================================== -->
  <xsl:template name="count-false">
    <xsl:param name="text"/>
    <xsl:variable name="normalized"
      select="normalize-space(translate($text, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))"/>
    <xsl:variable name="tokenCount"
      select="string-length($normalized) - string-length(translate($normalized, ' ', '')) + 1"/>
    <xsl:variable name="compact" select="translate($normalized, ' ', '')"/>
    <xsl:variable name="compactLength" select="string-length($compact)"/>
    <xsl:choose>
      <xsl:when test="$normalized = ''">0</xsl:when>
      <xsl:when test="translate($compact, 'truefals', '') = ''">
        <xsl:value-of select="$compactLength - 4 * $tokenCount"/>
      </xsl:when>
      <xsl:when test="translate($compact, '01', '') = ''">
        <xsl:value-of select="string-length(translate($compact, '1', ''))"/>
      </xsl:when>
      <xsl:otherwise>0</xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- Template to generate rows for result tables (iterative using position node-set trick) -->
  <xsl:template name="generate-result-rows">
    <xsl:param name="quantities"/>
    <xsl:param name="cmcValues"/>
    <xsl:param name="hasCmc"/>

    <xsl:variable name="firstQuantity" select="$quantities[1]"/>
    <xsl:variable name="firstQuantityValues" select="normalize-space($firstQuantity/si:realListXMLList/si:valueXMLList)"/>
    <xsl:variable name="totalTokens" select="string-length($firstQuantityValues) - string-length(translate($firstQuantityValues, ' ', '')) + 1"/>

    <xsl:for-each select="(//node())[position() &lt;= $totalTokens]">
      <xsl:variable name="currentIndex" select="position()"/>
      <tr>
        <xsl:for-each select="$quantities">
          <xsl:variable name="quantityValues" select="normalize-space(concat(si:realListXMLList/si:valueXMLList, dcc:charsXMLList))"/>
          <xsl:variable name="quantityUncertainties" select="normalize-space(si:realListXMLList/si:measurementUncertaintyUnivariateXMLList/si:expandedMUXMLList/si:valueExpandedMUXMLList | si:realListXMLList/si:expandedUncXMLList/si:uncertaintyXMLList)"/>
          <xsl:variable name="quantityCoverageFactors" select="normalize-space(si:realListXMLList/si:measurementUncertaintyUnivariateXMLList/si:expandedMUXMLList/si:coverageFactorXMLList | si:realListXMLList/si:expandedUncXMLList/si:coverageFactorXMLList)"/>
          <xsl:variable name="hasUncertainty" select="si:realListXMLList/si:measurementUncertaintyUnivariateXMLList | si:realListXMLList/si:expandedUncXMLList"/>

          <td>
            <xsl:call-template name="format-number-comma">
              <xsl:with-param name="number">
                <xsl:call-template name="get-token-at-position">
                  <xsl:with-param name="text" select="$quantityValues"/>
                  <xsl:with-param name="position" select="$currentIndex"/>
                </xsl:call-template>
              </xsl:with-param>
            </xsl:call-template>
          </td>

          <xsl:if test="$hasUncertainty">
            <td>
              <xsl:call-template name="format-number-comma">
                <xsl:with-param name="number">
                  <xsl:call-template name="get-token-at-position">
                    <xsl:with-param name="text" select="$quantityUncertainties"/>
                    <xsl:with-param name="position" select="$currentIndex"/>
                  </xsl:call-template>
                </xsl:with-param>
              </xsl:call-template>
            </td>
            <td>
              <xsl:call-template name="format-number-comma">
                <xsl:with-param name="number">
                  <xsl:call-template name="get-token-at-position">
                    <xsl:with-param name="text" select="$quantityCoverageFactors"/>
                    <xsl:with-param name="position" select="$currentIndex"/>
                  </xsl:call-template>
                </xsl:with-param>
              </xsl:call-template>
            </td>
          </xsl:if>
        </xsl:for-each>

        <!-- Coluna CMC: Sim/Não conforme dcc:valid(XMLList) -->
        <xsl:if test="$hasCmc">
          <xsl:variable name="cmcStatus">
            <xsl:call-template name="get-token-at-position">
              <xsl:with-param name="text" select="$cmcValues"/>
              <xsl:with-param name="position" select="$currentIndex"/>
            </xsl:call-template>
          </xsl:variable>
          <td>
            <xsl:if test="normalize-space($cmcStatus) = 'false' or normalize-space($cmcStatus) = '0'">
              <xsl:attribute name="class">cmc-fora</xsl:attribute>
            </xsl:if>
            <xsl:choose>
              <xsl:when test="normalize-space($cmcStatus) = 'true' or normalize-space($cmcStatus) = '1'">Sim</xsl:when>
              <xsl:when test="normalize-space($cmcStatus) = 'false' or normalize-space($cmcStatus) = '0'">Não</xsl:when>
              <xsl:otherwise>-</xsl:otherwise>
            </xsl:choose>
          </td>
        </xsl:if>
      </tr>
    </xsl:for-each>
  </xsl:template>

  <!-- Template to get token at specific position from space-separated text -->
  <xsl:template name="get-token-at-position">
    <xsl:param name="text"/>
    <xsl:param name="position"/>
    <xsl:param name="delimiter" select="' '"/>
    
    <xsl:choose>
      <xsl:when test="$position = 1">
        <xsl:choose>
          <xsl:when test="contains($text, $delimiter)">
            <xsl:value-of select="substring-before($text, $delimiter)"/>
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="$text"/>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:when>
      <xsl:otherwise>
        <xsl:call-template name="get-token-at-position">
          <xsl:with-param name="text" select="substring-after($text, $delimiter)"/>
          <xsl:with-param name="position" select="$position - 1"/>
          <xsl:with-param name="delimiter" select="$delimiter"/>
        </xsl:call-template>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- Helper template to convert scientific notation to decimal -->
  <xsl:template name="convert-scientific">
    <xsl:param name="mantissa"/>
    <xsl:param name="exponent"/>
    
    <!-- Check if mantissa is negative -->
    <xsl:variable name="isNegative" select="starts-with($mantissa, '-')"/>
    <xsl:variable name="absMantissa">
      <xsl:choose>
	<xsl:when test="$isNegative">
          <xsl:value-of select="substring($mantissa, 2)"/>
	</xsl:when>
	<xsl:otherwise>
          <xsl:value-of select="$mantissa"/>
	</xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    
    <xsl:variable name="mantissaNum" select="translate($absMantissa, '.', ',')"/>
    <xsl:variable name="expNum" select="number($exponent)"/>
    
    <xsl:if test="$isNegative">-</xsl:if>
    
    <xsl:choose>
      <!-- Positive exponent: move decimal point to the right -->
      <xsl:when test="$expNum &gt; 0">
	<xsl:variable name="intPart" select="substring-before(concat($absMantissa, '.'), '.')"/>
	<xsl:variable name="decPart" select="substring-after($absMantissa, '.')"/>
	<xsl:variable name="fullNumber" select="concat($intPart, $decPart)"/>
	<xsl:variable name="fullLength" select="string-length($fullNumber)"/>
	<xsl:variable name="decLength" select="string-length($decPart)"/>
	
	<xsl:choose>
          <xsl:when test="$expNum &gt;= $decLength">
            <!-- No decimal places left -->
            <xsl:value-of select="$fullNumber"/>
            <xsl:call-template name="add-zeros">
              <xsl:with-param name="count" select="$expNum - $decLength"/>
            </xsl:call-template>
          </xsl:when>
          <xsl:otherwise>
            <!-- Still has decimal places -->
            <xsl:value-of select="substring($fullNumber, 1, $expNum + string-length($intPart))"/>
            <xsl:text>,</xsl:text>
            <xsl:value-of select="substring($fullNumber, $expNum + string-length($intPart) + 1)"/>
          </xsl:otherwise>
	</xsl:choose>
      </xsl:when>
      
      <!-- Negative exponent: move decimal point to the left -->
      <xsl:when test="$expNum &lt; 0">
	<xsl:variable name="absExp" select="-1 * $expNum"/>
	<xsl:variable name="intPart" select="substring-before(concat($absMantissa, '.'), '.')"/>
	<xsl:variable name="decPart" select="substring-after($absMantissa, '.')"/>
	
	<xsl:text>0,</xsl:text>
	<xsl:call-template name="add-zeros">
          <xsl:with-param name="count" select="$absExp - 1"/>
	</xsl:call-template>
	<xsl:value-of select="$intPart"/>
	<xsl:value-of select="$decPart"/>
      </xsl:when>
      
      <!-- Exponent is 0: number stays the same -->
      <xsl:otherwise>
	<xsl:value-of select="translate($absMantissa, '.', ',')"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  
  <!-- Template to add zeros -->
  <xsl:template name="add-zeros">
    <xsl:param name="count"/>
    <xsl:if test="$count &gt; 0">
      <xsl:text>0</xsl:text>
      <xsl:call-template name="add-zeros">
        <xsl:with-param name="count" select="$count - 1"/>
      </xsl:call-template>
    </xsl:if>
  </xsl:template>

  <!-- Template to convert scientific notation to decimal format -->
  <xsl:template name="scientific-to-decimal">
    <xsl:param name="number"/>
    <xsl:variable name="normalizedNumber" select="normalize-space($number)"/>
    
    <xsl:choose>
      <!-- Check if it's scientific notation (contains E or e) -->
      <xsl:when test="contains($normalizedNumber, 'E') or contains($normalizedNumber, 'e')">
	<xsl:variable name="mantissa">
          <xsl:choose>
            <xsl:when test="contains($normalizedNumber, 'E')">
              <xsl:value-of select="substring-before($normalizedNumber, 'E')"/>
            </xsl:when>
            <xsl:otherwise>
              <xsl:value-of select="substring-before($normalizedNumber, 'e')"/>
            </xsl:otherwise>
          </xsl:choose>
	</xsl:variable>
	
	<xsl:variable name="exponentPart">
          <xsl:choose>
            <xsl:when test="contains($normalizedNumber, 'E')">
              <xsl:value-of select="substring-after($normalizedNumber, 'E')"/>
            </xsl:when>
            <xsl:otherwise>
              <xsl:value-of select="substring-after($normalizedNumber, 'e')"/>
            </xsl:otherwise>
          </xsl:choose>
	</xsl:variable>
	
	<!-- Handle exponent sign properly -->
	<xsl:variable name="exponent">
          <xsl:choose>
            <xsl:when test="starts-with($exponentPart, '+')">
              <xsl:value-of select="substring($exponentPart, 2)"/>
            </xsl:when>
            <xsl:when test="starts-with($exponentPart, '-')">
              <xsl:value-of select="$exponentPart"/> <!-- Already negative -->
            </xsl:when>
            <xsl:otherwise>
              <xsl:value-of select="$exponentPart"/>
            </xsl:otherwise>
          </xsl:choose>
	</xsl:variable>
	
	<!-- Convert scientific to decimal -->
	<xsl:call-template name="convert-scientific">
          <xsl:with-param name="mantissa" select="$mantissa"/>
          <xsl:with-param name="exponent" select="$exponent"/>
	</xsl:call-template>
      </xsl:when>
      <!-- If not scientific notation, just format with comma -->
      <xsl:otherwise>
	<xsl:call-template name="format-number-comma">
          <xsl:with-param name="number" select="$normalizedNumber"/>
	</xsl:call-template>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  
  
  <!-- Template to format numbers with comma as decimal separator -->
  <xsl:template name="format-number-comma">
    <xsl:param name="number"/>
    <xsl:variable name="normalizedNumber" select="normalize-space($number)"/>
    <xsl:variable name="lowerNumber"
      select="translate($normalizedNumber, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"/>

    <xsl:choose>
      <!-- Infinito (ex.: nueff = inf) -->
      <xsl:when test="$lowerNumber = 'inf' or $lowerNumber = '+inf' or $lowerNumber = 'infinity' or $lowerNumber = '+infinity'">
        <xsl:text>&#x221E;</xsl:text>
      </xsl:when>
      <xsl:when test="$lowerNumber = '-inf' or $lowerNumber = '-infinity'">
        <xsl:text>-&#x221E;</xsl:text>
      </xsl:when>
      <!-- Handle scientific notation -->
      <xsl:when test="contains($normalizedNumber, 'E') or contains($normalizedNumber, 'e')">
	<!-- Convert scientific notation to decimal -->
        <xsl:call-template name="scientific-to-decimal">
          <xsl:with-param name="number" select="$number"/>
        </xsl:call-template>
      </xsl:when>
      <!-- Handle regular decimal numbers -->
      <xsl:when test="contains($normalizedNumber, '.')">
        <xsl:call-template name="format-decimal-comma">
          <xsl:with-param name="number" select="$normalizedNumber"/>
        </xsl:call-template>
      </xsl:when>
      <!-- Handle integers -->
      <xsl:otherwise>
        <xsl:value-of select="$normalizedNumber"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <!-- Template to replace decimal point with comma -->
  <xsl:template name="format-decimal-comma">
    <xsl:param name="number"/>
    <xsl:variable name="integerPart" select="substring-before(concat($number, '.'), '.')"/>
    <xsl:variable name="decimalPart" select="substring-after($number, '.')"/>
    
    <xsl:value-of select="$integerPart"/>
    <xsl:if test="$decimalPart != ''">
      <xsl:text>,</xsl:text>
      <xsl:value-of select="$decimalPart"/>
    </xsl:if>
  </xsl:template>

  <!-- Template to format SI units to human-readable format -->
  <!-- TODO -->
  <!-- expandir para mais unidades -->
  <!-- generalizar para prefixos do SI -->
  <xsl:template name="format-unit">
    <xsl:param name="unit"/>
    <xsl:choose>
      <xsl:when test="$unit = '\degreecelsius'">ºC</xsl:when>
      <xsl:when test="$unit = '\percent'">%</xsl:when>
      <xsl:when test="$unit = '\micro\ampere'">&#xB5;A</xsl:when>
      <xsl:when test="$unit = '\milli\ampere'">mA</xsl:when>
      <xsl:when test="$unit = '\ampere'">A</xsl:when>
      <xsl:when test="$unit = '\kilo\ohm'">kΩ</xsl:when>
      <xsl:when test="$unit = '\ohm'">Ω</xsl:when>
      <xsl:when test="$unit = '\farad'">F</xsl:when>
      <xsl:when test="$unit = '\pico\farad'">pF</xsl:when>
      <xsl:when test="$unit = '\nano\farad'">nF</xsl:when>
      <xsl:when test="$unit = '\micro\farad'">&#xB5;F</xsl:when>
      <xsl:when test="$unit = '\hertz'">Hz</xsl:when>
      <xsl:when test="$unit = '\kilo\hertz'">kHz</xsl:when>
      <xsl:when test="$unit = '\volt'">V</xsl:when>
      <xsl:when test="$unit = '\milli\volt'">mV</xsl:when>
      <xsl:when test="$unit = '\micro\volt'">&#xB5;V</xsl:when>
      <xsl:when test="$unit = '\nano\second'">ns</xsl:when>
      <xsl:when test="$unit = '\second'">s</xsl:when>
      <xsl:when test="$unit = '\meter'">m</xsl:when>
      <xsl:when test="$unit = '\micro\volt\volt\tothe{-1}'">&#xB5;V/V</xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="$unit"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  
  <!-- Generic template to process measurement rows -->
  <xsl:template name="process-measurement-rows">
    <xsl:param name="resultNode"/>
    <xsl:param name="valueIndex"/>
    
    <xsl:variable name="frequencies" select="$resultNode/dcc:data/dcc:list/dcc:quantity[1]/si:realListXMLList/si:valueXMLList"/>
    <xsl:variable name="voltages" select="$resultNode/dcc:data/dcc:list/dcc:quantity[2]/si:realListXMLList/si:valueXMLList"/>
    <xsl:variable name="values" select="$resultNode/dcc:data/dcc:list/dcc:quantity[$valueIndex]/si:realListXMLList/si:valueXMLList"/>
    <xsl:variable name="uncertainties" select="$resultNode/dcc:data/dcc:list/dcc:quantity[$valueIndex]/si:realListXMLList/si:measurementUncertaintyUnivariateXMLList/si:expandedMUXMLList/si:valueExpandedMUXMLList | $resultNode/dcc:data/dcc:list/dcc:quantity[$valueIndex]/si:realListXMLList/si:expandedUncXMLList/si:uncertaintyXMLList"/>
    <xsl:variable name="coverageFactors" select="$resultNode/dcc:data/dcc:list/dcc:quantity[$valueIndex]/si:realListXMLList/si:measurementUncertaintyUnivariateXMLList/si:expandedMUXMLList/si:coverageFactorXMLList | $resultNode/dcc:data/dcc:list/dcc:quantity[$valueIndex]/si:realListXMLList/si:expandedUncXMLList/si:coverageFactorXMLList"/>
    
    <xsl:call-template name="generate-table-rows">
      <xsl:with-param name="frequencies" select="$frequencies"/>
      <xsl:with-param name="voltages" select="$voltages"/>
      <xsl:with-param name="values" select="$values"/>
      <xsl:with-param name="uncertainties" select="$uncertainties"/>
      <xsl:with-param name="coverageFactors" select="$coverageFactors"/>
      <xsl:with-param name="index" select="1"/>
    </xsl:call-template>
  </xsl:template>

  <!-- Template to generate table rows from tokenized data -->
  <xsl:template name="generate-table-rows">
    <xsl:param name="frequencies"/>
    <xsl:param name="voltages"/>
    <xsl:param name="values"/>
    <xsl:param name="uncertainties"/>
    <xsl:param name="coverageFactors"/>
    <xsl:param name="index"/>
    
    <xsl:variable name="freqTokens" select="normalize-space($frequencies)"/>
    <xsl:variable name="voltTokens" select="normalize-space($voltages)"/>
    <xsl:variable name="valueTokens" select="normalize-space($values)"/>
    <xsl:variable name="uncertTokens" select="normalize-space($uncertainties)"/>
    <xsl:variable name="coverageTokens" select="normalize-space($coverageFactors)"/>
    
    <xsl:if test="$freqTokens != ''">
      <xsl:variable name="currentFreq" select="substring-before(concat($freqTokens, ' '), ' ')"/>
      <xsl:variable name="currentVolt" select="substring-before(concat($voltTokens, ' '), ' ')"/>
      <xsl:variable name="currentValue" select="substring-before(concat($valueTokens, ' '), ' ')"/>
      <xsl:variable name="currentUncert" select="substring-before(concat($uncertTokens, ' '), ' ')"/>
      <xsl:variable name="currentCoverage" select="substring-before(concat($coverageTokens, ' '), ' ')"/>
      
      <xsl:if test="$currentFreq != ''">
        <tr>
          <td><xsl:value-of select="$currentVolt"/></td>
          <td><xsl:value-of select="$currentFreq"/></td>
          <td>
            <xsl:choose>
              <xsl:when test="contains($currentValue, '.')">
                <xsl:call-template name="format-number">
                  <xsl:with-param name="number" select="$currentValue"/>
                </xsl:call-template>
              </xsl:when>
              <xsl:otherwise>
                <xsl:value-of select="$currentValue"/>
              </xsl:otherwise>
            </xsl:choose>
          </td>
          <td><xsl:value-of select="$currentUncert"/></td>
          <td><xsl:value-of select="$currentCoverage"/></td>
          <td>∞</td>
        </tr>
        
        <!-- Recursive call for next token -->
        <xsl:call-template name="generate-table-rows">
          <xsl:with-param name="frequencies" select="substring-after($freqTokens, ' ')"/>
          <xsl:with-param name="voltages" select="substring-after($voltTokens, ' ')"/>
          <xsl:with-param name="values" select="substring-after($valueTokens, ' ')"/>
          <xsl:with-param name="uncertainties" select="substring-after($uncertTokens, ' ')"/>
          <xsl:with-param name="coverageFactors" select="substring-after($coverageTokens, ' ')"/>
          <xsl:with-param name="index" select="$index + 1"/>
        </xsl:call-template>
      </xsl:if>
    </xsl:if>
  </xsl:template>

  <!-- Template to format numbers with spaces for thousands and comma for decimal -->
  <xsl:template name="format-number">
    <xsl:param name="number"/>
    <xsl:variable name="integerPart" select="substring-before(concat($number, '.'), '.')"/>
    <xsl:variable name="decimalPart" select="substring-after($number, '.')"/>
    
    <xsl:value-of select="$integerPart"/>
    <xsl:if test="$decimalPart != ''">
      <xsl:text>,</xsl:text>
      <xsl:value-of select="$decimalPart"/>
    </xsl:if>
  </xsl:template>
  
</xsl:stylesheet>
