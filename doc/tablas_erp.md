# Descripción de Tablas ERP

## Archivo: estructura de tablas guias.xlsx

### Tabla: WH_Transaction

| Columna | Tipo de Dato | Ejemplo |
| --- | --- | --- |
| Transaction | str | DSASSAL000000042834 |
| Company | str | DSAS |
| WareHouse | str | LIMADSAS000000000162 |
| Application | str | WH |
| TransactionType | str | LIMADSAS000000000127 |
| DocumentType | str | LIMADSAS000000000004 |
| DocumentSerie | str | T001 |
| DocumentNo | Integer | 7486 |
| TransactionDate | DateTime | 2026-04-09 00:00:00 |
| TransactionCurrency | str | LO |
| ServiceType | str | LIMADSAS000000000201 |
| Period | Integer | 202604 |
| ExchangeRate | Float / Decimal | 3.335 |
| DocRef | Float / Decimal |  |
| DocRef1 | Float / Decimal |  |
| FechaFactura | Float / Decimal |  |
| FechaTraslado | DateTime | 2026-04-09 00:00:00 |
| Employee | Float / Decimal |  |
| Situation | Integer | 9 |
| Production | Float / Decimal |  |
| SaleDoc | Float / Decimal |  |
| SaleDocType | Float / Decimal |  |
| SaleDocAbbrev | Float / Decimal |  |
| SaleDocSerie | Float / Decimal |  |
| SaleDocNo | Float / Decimal |  |
| Driver | str | COYLA ROBLES FREDY |
| LicenciaConducir | str | Q43594207 |
| NroInscripcion | str | isamisa |
| VehicleID | str | B5W920 |
| Marca | str | HINO |
| Transportista | str | GRUPO ISAMISA S.A.C. |
| RucTransportista | Integer | 20602674488 |
| AddressTransportista | str | Av metropolitana 1006 - ate |
| MotivoTraslado | str | TRASLADOS ENTRE ESTABLECIMIENTOS DE LA EMPRESA |
| WareHouseTarget | str | LIMADSAS000000000052 |
| TargetType | str | P |
| TargetAddress | str | PAMPAS TINAJAS - S/N QUEBRADAS- Lima  - Lima |
| TargetPerson | str | LIMADSAS000000178094 |
| TargetPersonRUC | Integer | 20602674488 |
| TargetPersonName | str | GRUPO ISAMISA S.A.C. |
| Total | Float / Decimal | 2912.3131 |
| TotalLo | Float / Decimal | 2912.3131 |
| TotalEx | Float / Decimal | 847.0951 |
| Comments | Float / Decimal |  |
| Voucher | Float / Decimal |  |
| VoucherNo | Float / Decimal |  |
| VoucherDate | Float / Decimal |  |
| VoucherStatus | Float / Decimal |  |
| VoucherVoid | Float / Decimal |  |
| VoucherVoidNo | Float / Decimal |  |
| VoucherVoidDate | Float / Decimal |  |
| RejectionDate | Float / Decimal |  |
| RejectionUser | Float / Decimal |  |
| RejectionReason | Float / Decimal |  |
| ApproveUser | str | nrivas |
| ApproveDate | DateTime | 2026-04-08 11:55:50.957000 |
| Status | str | A |
| XLastUser | str | dhuanacuni |
| XLastDate | DateTime | 2026-04-08 15:13:42.420000 |
| ReplicationUnit | str | LIMA |
| FlagFacturado | str | N |
| RegisterUser | str | dhuanacuni |
| TransactionDateSystem | DateTime | 2026-04-08 15:11:57.293000 |
| TransactionUser | Float / Decimal |  |
| TransactionReason | str | COCINA T2 |
| FlagDelivery | str | N |
| DocumentCC | Float / Decimal |  |
| ApDocument | Float / Decimal |  |
| flagexittype | Float / Decimal |  |
| flagcustomertype | Float / Decimal |  |
| transactionref | Float / Decimal |  |
| numberop | Float / Decimal |  |
| numberoc | Float / Decimal |  |
| DocRefOrders | Float / Decimal |  |
| SubWareHouse | str | LIMADSAS000000000109 |
| SubWareHouseTarget | str | LIMADSAS000000000012 |
| NroOrder | Float / Decimal |  |
| useconfir | str | Y |
| Transport | str | LIMADSAS000000000001 |
| Vehicle | str | LIMEDSAS000000000028 |
| DriverId | str | LIMEDSAS000000000104 |
| id_guia_remision | Integer | 2198124 |
| PesoBruto | Float / Decimal | 130.0 |
| motivo | Float / Decimal |  |
| iselectro | str | Y |
| origenaddress | str | AV. SAN CARLOS MZA. C LOTE. 15 URB. SANTA MARTH... |
| project | Float / Decimal |  |
| etapa | Float / Decimal |  |
| ubigeo_des | Float / Decimal | 150109.0 |
| envio_nube | str |   aceptada |
| phone | Float / Decimal |  |
| correlativo | Float / Decimal |  |

### Tabla: WH_TransactionDetail

| Columna | Tipo de Dato | Ejemplo |
| --- | --- | --- |
| Line | Integer | 21 |
| Transaction | str | CAR1DSAS000000012405 |
| Unit | str | KG |
| QuantityBultos | Float / Decimal | 107.0 |
| UnitBultos | str | PZAS |
| Item | str | LIMADSAS000000010606 |
| FlagItemClass | str | A |
| Condition | Integer | 0 |
| Lot | Integer | 0 |
| LotDueDate | DateTime | 2026-04-08 15:29:33.410000 |
| LotLivestock | Float / Decimal |  |
| Location | Float / Decimal |  |
| Project | Float / Decimal |  |
| ProjectCode | Float / Decimal |  |
| CostCenter | Float / Decimal |  |
| CostCenterCode | Float / Decimal |  |
| ARF1 | Float / Decimal |  |
| ARF1Code | Float / Decimal |  |
| ARF1Value | Float / Decimal |  |
| ARF2 | Float / Decimal |  |
| ARF2Code | Float / Decimal |  |
| ARF2Value | Float / Decimal |  |
| ARF3 | Float / Decimal |  |
| ARF3Code | Float / Decimal |  |
| ARF3Value | Float / Decimal |  |
| PriceLo | Float / Decimal | 17.7966 |
| PriceEx | Float / Decimal | 5.1764 |
| Quantity | Float / Decimal | 4.95 |
| TotalLo | Float / Decimal | 88.0932 |
| TotalEx | Float / Decimal | 25.6234 |
| TotalTax | Float / Decimal | 103.95 |
| TotalTaxLo | Float / Decimal |  |
| TotalTaxEx | Float / Decimal |  |
| ItemCode | String / Mixed | ABPAPO007 |
| ItemDescription | str | FILETE DE PAVITA JR. |
| Price | Float / Decimal | 17.7966 |
| Total | Float / Decimal | 88.0932 |
| XLastUser | str | nrivas |
| XLastDate | DateTime | 2026-04-08 11:55:50.957000 |
| ReplicationUnit | str | LIMA |
| Company | str | DSAS |
| Comments | Float / Decimal |  |
| Comments01 | Float / Decimal |  |
| quantitydispatch | Float / Decimal |  |
| quantitydoc | Float / Decimal | 4.95 |
| unitdoc | str | KG |
| unitfactor | Integer | 1 |
| pricedoc | Float / Decimal | 17.7966 |
| totaldoc | Float / Decimal | 88.0932 |
| EmployeeLocation | Float / Decimal |  |
| Age | Float / Decimal |  |
| ChargeDate | Float / Decimal |  |
| ChargeHour | Float / Decimal |  |
| FlagDateControl | Float / Decimal |  |
| Warehouse | Float / Decimal |  |
| CodCosto | String / Mixed | 32 |
| OrderRequisition | Float / Decimal |  |
| kardex2 | str | LIMADCAR000000159785 |
| motivo | str | GENERAL |
| codlote | Float / Decimal |  |
| pesada | Float / Decimal |  |

## Archivo: estructura de tablas retenciones.xlsx

### Tabla: AP_Retencion

| Columna | Tipo de Dato | Ejemplo |
| --- | --- | --- |
| Id | Integer | 3866 |
| Serie | str | R001 |
| Numero | Integer | 3830 |
| Vendor | str | LIMADSAS000000209159 |
| VendorRuc | Integer | 20604496838 |
| VendorName | str | GRUPO SADDA E.I.R.L. |
| VendorAddress | str |  MZA. E LOTE 2 OTR. ASOC. LAS BEGONIAS DE SAN L... |
| DocumentDate | DateTime | 2026-04-01 00:00:00 |
| Tasa | Integer | 3 |
| TotalRetenido | Float / Decimal | 50.93 |
| TotalPagado | Float / Decimal | 1646.92 |
| Obs | Float / Decimal |  |
| XlastUser | str | aventura |
| XlastDate | DateTime | 2026-04-07 11:30:43.480000 |
| status | str | enviado |

### Tabla: AP_Retencion_Status

| Columna | Tipo de Dato | Ejemplo |
| --- | --- | --- |
| id | Integer | 4518 |
| Retencion | Integer | 3841 |
| Status | str | aceptada |
| Pdf | str | https://www.nubefact.com/retencion/713dd106-ddd... |
| Xml | str | https://www.nubefact.com/retencion/713dd106-ddd... |
| Cdr | str | https://www.nubefact.com/retencion/713dd106-ddd... |
| Aceptacion | str | https://www.nubefact.com/retencion/713dd106-ddd... |
| Descripcion | str | El Comprobante de Retención R001-3805 ha sido A... |
| Nota | Float / Decimal |  |
| ResponseCode | Integer | 0 |
| Soap | Float / Decimal |  |
| error | Float / Decimal |  |
| XlastUser | str | fary |
| XlastDate | DateTime | 2026-03-28 11:19:08.580000 |

### Tabla: AP_RetencionDetail

| Columna | Tipo de Dato | Ejemplo |
| --- | --- | --- |
| ID | Integer | 9651 |
| Retencion | Integer | 3817 |
| DRserie | str | F001 |
| DRnumero | Integer | 42279 |
| DRfecha | DateTime | 2026-02-23 00:00:00 |
| DRmoneda | str | EX |
| DRtotal | Float / Decimal | 247.8 |
| DRpagoFecha | DateTime | 2026-03-19 00:00:00 |
| DRpagoNro | Integer | 1 |
| DRpagoTotal | Float / Decimal | 247.8 |
| TipoCambio | Float / Decimal | 3.435 |
| TipoCambioFecha | DateTime | 2026-03-19 00:00:00 |
| Retenido | Float / Decimal | 25.5357 |
| RetenidoFecha | DateTime | 2026-03-19 00:00:00 |
| Pagado | Float / Decimal | 825.6543 |

## Archivo: estructura tablas de ventas.xlsx

### Tabla: AR_Document

| Columna | Tipo de Dato | Ejemplo |
| --- | --- | --- |
| Document | str | DLV1DSAS000000135404 |
| DocumentNo | Integer | 86947 |
| DocumentSerie | str | B037 |
| Company | str | DSAS |
| Vendor | str | DUMMY |
| VendorName | str | CLIENTE TEMPORAL |
| VendorRUC | Integer | 99999999 |
| VendorAddress | str | AV. METROPOLITANA MZA. S LOTE 13 A.V. LOS ANGELES  |
| VendorTelephone | Float / Decimal | 999074396.0 |
| VendorParent | Float / Decimal |  |
| VendorParentName | Float / Decimal |  |
| VendorParentRuc | Float / Decimal |  |
| PlazoDias | Integer | 0 |
| Collector | str | ppariona |
| DocumentType | str | LIMADSASBOLETA |
| DocumentDate | DateTime | 2026-04-08 22:29:41.857000 |
| Period | Integer | 202604 |
| FlagSaleType | str | C |
| FlagDetail | str | Y |
| FlagLetter | Float / Decimal |  |
| Reclaim | Float / Decimal |  |
| Situation | Integer | 9 |
| BUResponsible | str | CHUL |
| EMResponsible | str | ppariona |
| RegisterDate | DateTime | 2026-04-08 22:29:41.857000 |
| RegisterUser | str | ppariona |
| DueDate | DateTime | 2026-04-08 22:29:41.857000 |
| PaymentDate | Float / Decimal |  |
| RejectionDate | Float / Decimal |  |
| RejectionUser | Float / Decimal |  |
| RejectionReason | Float / Decimal |  |
| DocumentCurrency | str | LO |
| NroOrder | Float / Decimal |  |
| RefDoc | Float / Decimal |  |
| RefDocType | Float / Decimal |  |
| RefDocSerie | Float / Decimal |  |
| RefDocNo | Float / Decimal |  |
| RefGuides | Float / Decimal |  |
| ExchangeRate | Float / Decimal | 3.737 |
| DiscountGen | Float / Decimal |  |
| AmountTotDiscountLO | Float / Decimal | 0.0 |
| AmountTotDiscountEX | Integer | 0 |
| AmountImponibleLo | Float / Decimal | 3.39 |
| AmountImponibleEx | Float / Decimal | 0.91 |
| AmountNoImponibleLo | Float / Decimal | 0.0 |
| AmountNoImponibleEx | Float / Decimal | 0.0 |
| AmountNetLo | Float / Decimal | 3.39 |
| AmountNetEx | Float / Decimal | 0.91 |
| AmountTaxLo | Float / Decimal | 0.61 |
| AmountTaxEx | Float / Decimal | 1.0738 |
| AmountTotalLo | Float / Decimal | 4.0 |
| AmountTotalEx | Float / Decimal | 1.0704 |
| PaymentLo | Float / Decimal | 4.0 |
| PaymentEx | Float / Decimal | 0.0 |
| PaymentAdelantolo | Integer | 0 |
| PaymentAdelantoex | Integer | 0 |
| PaymentStatus | str | P |
| Financelo | Integer | 0 |
| Financeex | Integer | 0 |
| Voucher | Float / Decimal |  |
| VoucherDate | Float / Decimal |  |
| VoucherVoid | Float / Decimal |  |
| VoucherVoidDate | Float / Decimal |  |
| VoucherVoidNo | Float / Decimal |  |
| VoucherStatus | str | P |
| VoucherNo | Float / Decimal | 0.0 |
| Comments | str | Mesa N°: 18   Pedido = N° 40272  Moza: lisuiza |
| LastPayrollNumber | Float / Decimal |  |
| FinanceSourceProcess | Float / Decimal |  |
| FinanceTargetProcess | Float / Decimal |  |
| NegotiationType | str | CA |
| NegotiationBank | Float / Decimal |  |
| NegotiationDate | Float / Decimal |  |
| NegotiationDocument | Float / Decimal |  |
| NegotiationDocExternal | Float / Decimal |  |
| NegotiationFlagProtesto | str | N |
| NegotiationUserProtesto | Float / Decimal |  |
| NegotiationDateProtesto | Float / Decimal |  |
| NegotiationNumber | Float / Decimal |  |
| Application | str | AR |
| Warehouse | str | LIMADSAS000000000149 |
| FlagDelivered | str | E |
| AmountSaleLo | Float / Decimal | 3.39 |
| AmountSaleEx | Float / Decimal | 0.91 |
| DocumentCC | Float / Decimal |  |
| CustomerAddressDelivered | Float / Decimal |  |
| Status | str | C |
| ReplicationUnit | str | LIMA |
| XLastUser | str | ppariona |
| XLastDate | DateTime | 2026-04-08 22:29:41.857000 |
| FlagVoucher | str | Y |
| PaymentIniLo | Float / Decimal |  |
| PaymentIniEx | Float / Decimal |  |
| adjustlo | Float / Decimal |  |
| adjustex | Float / Decimal |  |
| adjust | Float / Decimal |  |
| CollectorName | Float / Decimal |  |
| EMResponsibleName | Float / Decimal |  |
| FlagExitType | str | V |
| FlagCustomerType | str | L |
| FlagNCType | Float / Decimal |  |
| TRANSACTION | Float / Decimal |  |
| commission | Float / Decimal |  |
| COMMENTS2 | Float / Decimal |  |
| flagkeep | Float / Decimal |  |
| keepdocno | Float / Decimal |  |
| keeplo | Float / Decimal |  |
| keepex | Float / Decimal |  |
| flagxmayor | Float / Decimal |  |
| turn | str | T220260408 |
| Sector | Float / Decimal |  |
| Departament | Float / Decimal |  |
| anticipo | Float / Decimal |  |
| saldo | Float / Decimal |  |
| PersonRep | Float / Decimal |  |
| SubBusinessUnit | str | CHUL |
| AccountSalesLine | Float / Decimal |  |
| flagTAX | str | N |
| VendorEmail | Float / Decimal |  |
| NroDespa | Float / Decimal |  |
| PreCuenta | Float / Decimal | 40272.0 |
| Relacionado | Float / Decimal |  |
| VendorAddressDelivery | Float / Decimal |  |
| SalesType | str | L |
| ViaType | Float / Decimal |  |
| Destination | Float / Decimal |  |
| CountryTarget | Float / Decimal |  |
| Carrier | Float / Decimal |  |
| BoardingDate | Float / Decimal |  |
| BillNumber | Float / Decimal |  |
| GrossWeight | Float / Decimal |  |
| NetWeight | Float / Decimal |  |
| Capacity | Float / Decimal |  |
| Incoterm | Float / Decimal |  |
| CondicionPago | Float / Decimal |  |
| PartidaAranc | Float / Decimal |  |
| NroAWB | Float / Decimal |  |
| AmountRounded | Float / Decimal | 0.0 |
| id_cab_cpe | Integer | 1736878 |
| driver | Float / Decimal |  |
| DepartmentTarget | Float / Decimal |  |
| Distrito | str | ATE - VITARTE |
| PayType | Float / Decimal |  |
| SaldoP | Float / Decimal |  |
| t_cobro | str | T |
| nrodetrac | Float / Decimal |  |
| fechadetrac | Float / Decimal |  |
| montodetrac | Float / Decimal |  |
| vendedor | str | DENIS PILAR GONZALES CHIPANA |
| puntos | Integer | 0 |
| clase | Float / Decimal |  |
| t_venta_ch | str | Mesa |
| detraccion | Float / Decimal |  |
| condition | Float / Decimal |  |
| d_cod | Float / Decimal |  |
| d_tasa | Float / Decimal |  |
| MontoInafecto | Float / Decimal | 0.0 |
| tasa_icbper | Integer | 0 |
| v_ave | Float / Decimal |  |
| MotivoNC | Float / Decimal |  |
| fe | Float / Decimal |  |
| v_anticipo | str | N |
| RefAnticipo | Float / Decimal |  |
| tipovale | Float / Decimal |  |
| typeDocSun | str | T |
| juntos | Float / Decimal | 1.0 |
| duedate2 | DateTime | 2026-04-15 22:29:41.857000 |

### Tabla: AR_DocumentDetail

| Columna | Tipo de Dato | Ejemplo |
| --- | --- | --- |
| Document | str | ASESDSSA000000948972 |
| Line | Integer | 1 |
| Item | str | LIMADSAS0000009622 |
| ItemCode | str | ACREPA002 |
| Description | str | PAVO DE RECRIA NEGRO |
| Comments | Float / Decimal |  |
| Comments2 | Float / Decimal |  |
| Comments3 | Float / Decimal |  |
| Unit | str | PARES |
| UnitBultos | str | PQT |
| QuantityBultos | Float / Decimal | 0.0 |
| Discount | Integer | 0 |
| DiscountGen | Float / Decimal |  |
| Price | Float / Decimal | 39.8305 |
| PriceDiscount | Float / Decimal | 39.8305 |
| PriceLo | Float / Decimal | 39.8305 |
| PriceEx | Float / Decimal | 11.5854 |
| PriceTax | Float / Decimal | 47.0 |
| PriceTaxLo | Float / Decimal | 47.0 |
| PriceTaxEx | Float / Decimal | 13.6707 |
| Quantity | Float / Decimal | 46.0 |
| AmountImponibleLo | Float / Decimal | 1832.203 |
| AmountImponibleEx | Float / Decimal | 532.927 |
| AmountNoImponibleLo | Integer | 0 |
| AmountNoImponibleEx | Integer | 0 |
| AmountNetLo | Float / Decimal | 1832.203 |
| AmountNetEx | Float / Decimal | 532.927 |
| AmountDiscountLo | Float / Decimal | 0.0 |
| AmountDiscountEx | Float / Decimal | 0.0 |
| Tax1 | str | LIMADSAS000000000001 |
| Tax1Code | str | IGV |
| Tax1Rate | Integer | 18 |
| Tax1Lo | Integer | 0 |
| Tax1Ex | Integer | 0 |
| Tax2 | Float / Decimal |  |
| Tax2Code | Float / Decimal |  |
| Tax2Rate | Float / Decimal |  |
| Tax2Lo | Float / Decimal |  |
| Tax2Ex | Float / Decimal |  |
| Tax3 | Float / Decimal |  |
| Tax3Code | Float / Decimal |  |
| Tax3Rate | Float / Decimal |  |
| Tax3Lo | Float / Decimal |  |
| Tax3Ex | Float / Decimal |  |
| TotalTaxLo | Float / Decimal | 2162.0 |
| TotalTaxEx | Float / Decimal | 628.854 |
| Total | Float / Decimal | 1832.2034 |
| TotalLo | Float / Decimal | 1832.2 |
| TotalEx | Float / Decimal | 532.927 |
| Lot | Integer | 0 |
| LotDueDate | Float / Decimal |  |
| Project | Float / Decimal |  |
| ProjectCode | Float / Decimal |  |
| ARF1 | Float / Decimal |  |
| ARF1Code | Float / Decimal |  |
| ARF2 | Float / Decimal |  |
| ARF2Code | Float / Decimal |  |
| ARF3 | Float / Decimal |  |
| ARF3Code | Float / Decimal |  |
| Company | str | DSAS |
| XLastUser | str | dgonzales |
| XLastDate | DateTime | 2026-04-08 20:07:08.367000 |
| ReplicationUnit | str | LIMA |
| PriceDiscountGen | Float / Decimal |  |
| SubTotal | Float / Decimal | 1832.2034 |
| SubTotaltax | Float / Decimal | 2162.0 |
| pricedoc | Float / Decimal | 47.0 |
| quantitydoc | Float / Decimal | 46.0 |
| unitdoc | str | PARES |
| totaldoc | Float / Decimal | 2162.0 |
| unitfactor | Integer | 1 |
| discountdoc | Integer | 0 |
| ChargingDate | Float / Decimal |  |
| BirthDate | Float / Decimal |  |
| BusinessUnit | Float / Decimal |  |
| Period | Float / Decimal |  |
| PreCuenta | Float / Decimal |  |
| PreCuentaDet | Float / Decimal |  |
| tasa_icbper | Float / Decimal | 0.0 |
| inafecto | str | N |
| r_chul | String / Mixed | 0 |
| SerieAnticipo | Float / Decimal |  |
| DocumentoAnticipo | Float / Decimal |  |


## Archivo: ar_fe_nube.xlsx

### Tabla: AR_FE_Nube

| Columna | Tipo de Dato | Ejemplo |
| --- | --- | --- |
| id | int64 | 427622 |
| serie | str | B036 |
| numero | int64 | 222744 |
| enlace | str |  |
| aceptada_por_sunat | float64 |  |
| sunat_description | float64 |  |
| sunat_note | float64 |  |
| sunat_responsecode | float64 |  |
| sunat_soap_error | float64 |  |
| pdf_zip_base64 | float64 |  |
| xml_zip_base64 | float64 |  |
| cdr_zip_base64 | float64 |  |
| codigo_hash_qr | str |  |
| codigo_hash | str |  |
| error | str | Este documento ya existe |
| web | str | N |
