# Справочник Stutzen API (api1c) — извлечено из /Admin/Api/ApiDoc2

> Авторизация: заголовок `ApiKey` на всех эндпоинтах. Базовый URL: `https://www.catalog.stutzen.ru/api1c/`.
> Актуальность подтверждена: пример ответа одного из эндпоинтов содержит дату 2026-05-08, т.е. документация не архивная.

## RoboStorage
- **GET** `https://www.catalog.stutzen.ru/api1c/RoboStorage/GetStockTasks?count=x1&lastminut=x2&DateLastChange=false` — Задания склада _(п.11.1.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/RoboStorage/GetStockTasks?DTStart=x1&DTStart=x2` — Задания склада за период _(п.11.1.2)_
- **GET** `https://www.catalog.stutzen.ru/api1c/RoboStorage/GetStockTaskPositions?dcc_id=8339132` — Позиции задания _(п.11.2)_
- **POST** `https://www.catalog.stutzen.ru/api1c/RoboStorage/CreateStockTask` — Создать задание на склад _(п.11.3)_
- **POST** `https://www.catalog.stutzen.ru/api1c/RoboStorage/CreateStockTask2?stk_id=174634&comment_manager=comment&comment_stock=comment3&stockId=1&provider=TEST` — Создать задание (упрощенно) _(п.11.4)_
- **POST** `https://www.catalog.stutzen.ru/api1c/RoboStorage/GetPositionsLog?startDate=x1&endDate=x2` — Получить лог позиций _(п.11.5)_
- **GET** `https://www.catalog.stutzen.ru/api1c/RoboStorage/GetPositionsStorageHonestSignCodesLogs?dtStart=x1&dtStop=x2` — Получить лог позиций чс _(п.11.6)_
- **GET** `https://www.catalog.stutzen.ru/api1c/RoboStorage/GetPositionsStorageHonestSignCode` — Получить ЧС по коду _(п.11.8)_
- **POST** `https://www.catalog.stutzen.ru/api1c/RoboStorage/GetPositionsStorageHonestSignCode` — Получить ЧС по коду _(п.11.8.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/RoboStorage/GetPositionsStorageHonestSignCodes` — Получить ЧС по массиву кодов _(п.11.9)_

## Warehouse
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/goodsarrival?count=x` — Приход товара - последние измененные _(п.2.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/goodsarrival2?startDate=date1&stopDate=date2&count=x` — Приход товара за период _(п.2.1.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/arrival_positions?dcc_dcm_id=x` — Приход товара - позиции _(п.2.2)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/shipments?min=x` — Отгрузки - измененные _(п.2.3)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/shipments_userlogins?dcm_userlogins=x` — Отгрузки по менеджерам _(п.2.3.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/getclientshipments?cst_id=x&count=x2` — Получить список последних отгрузок клиента _(п.2.3.2)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/shipments_positions?dcc_dcm_id=x` — Отгрузки - позиции _(п.2.4)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/goodsarrival_set_external_num?ExternalNumber=x` — Задать внешний номер документа (требует доработки) _(п.2.5)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/goodsarrival_update?rcp_id=r&externalNumber=e&datetime=d&documentHeld=true&documentHeldCancel=true` — Обновление прихода _(п.2.6)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/positionsforshipment?cst_id=x1&pst_state_id=x2` — Позиции для отгрузки _(п.2.7)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/GetPositionsShipmentsNoArch?cst_id=x1` — Позиции для отгрузки (без архива) _(п.2.7.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/createshipment?username=x1&password=x2&positions=7978331,7978299&cst_id=x3` — Создать отгрузку _(п.2.8)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/createshipment2` — Создать отгрузку - новый метод _(п.2.8.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/GetPositionsModified` — Позиции со статусами прибытия _(п.2.9)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/GetPositions?pst_states=x1&dateTimeStart=x2&dateTimeStop=x3&mode=x4` — Получить список позиций _(п.2.10)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/GetPositions2?pst_ids=9144557,9092516` — Позиции по референсам _(п.2.10.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/GetPositions3` — Получить позиции (массив) _(п.2.10.2)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/GetOrderStates` — Список статусов _(п.2.11)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/GetInvoice?inv_id=x1` — Получить отгрузку _(п.2.12)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/PositionEditClientComment?pst_id=x1&pst_comment=x2` — Редактировать комментарий клиента _(п.2.13)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/PositionEditClientComment2` — Массовое редактирование комментария клиента _(п.2.13.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/PositionEditManagerComment?pst_id=x1&pst_manager_comment=x2` — Редактировать комментарий менеджера _(п.2.14)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/PositionEditManagerComment2` — Массовое редактирование комментария менеджера _(п.2.14.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/PositionEditProviderComment?pst_pst_id=x1&pst_comment_provider=x2` — Редактировать комментарий поставщика _(п.2.15)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/PositionEditProviderComment2` — Массовое редактирование комментария поставщика _(п.2.15.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/PositionEditStateID` — Редактировать статус позиции _(п.2.16)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/PositionsSetStatuses` — Редактировать статусы позиций _(п.2.17)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/GetPositionsHistory?psh_pst_id=x1` — История изменения статуса позиции _(п.2.18)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/GetAllPositionsHistory?minutes=x1&psh_state_id=x2` — История изменения статусов позиций _(п.2.19)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/GetAllPositionsHistoryClients?minutes=x1` — История статусов (со стороны клиента) _(п.2.19.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Warehouse/CheckPositionsShipments?pricelist_ids=x1` — Проверить позиции в отгрузке _(п.2.20)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Warehouse/CreateStockTask` — Создать задание на склад _(п.2.21)_

## HonestSign
- **GET** `https://www.catalog.stutzen.ru/api1c/HonestSign/GetOne?id=1` — Получить код маркировки _(п.19.1)_

## Provider
- **GET** `https://www.catalog.stutzen.ru/api1c/Provider/GetReconciliation?dcm_dct_id=15&dcm_deleted=0&grpprov_id=10&limit=0&provider_id=3` — Сверка с поставщиками _(п.5.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Provider/getprovidersstat?DTStart=2023-03-01T00:00:01&DTStop=2023-03-01T23:23:59` — Статистика поставщиков за период _(п.5.2)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Provider/GetOrders?dtime=2023-03-01T00:00:01&dtstop=2023-03-01T00:00:01&countLastOrders=1000&last_minutes_modified=x3&positions=true` — Заказы поставщикам _(п.5.3)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Provider/GetOrders2?dtime=2023-03-01T00:00:01&dtstop=2023-03-01T00:00:01&countLastOrders=1000&last_minutes_modified=x3&positions=true` — Заказы поставщикам (с историей) _(п.5.3.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Provider/GetPositionsInOrder?pst_ord_id=2537815` — Позиции в заказе поставщика _(п.5.4)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Provider/GetPositionsProvider?provider_id=x1&day=x2` — Позиции поставщика в работе _(п.5.5)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Provider/CreateOrder` — Создать заказ поставщику _(п.5.6)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Provider/CreateReceipt` — Оформить приход _(п.5.8)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Provider/GetPstIdClient?pst_id_provider=x1` — Позиция клиента по позиции поставщика _(п.5.9)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Provider/PositionsSetStatus` — Редактировать статус позиций _(п.5.10)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Provider/DivPosition` — Поделить позицию _(п.5.11)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Provider/DivPosition2` — Поделить позицию + смена статуса _(п.5.11.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Provider/DivPosition3` — Поделить список позиций _(п.5.11.2)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Provider/PositionUpdatePrice` — Поменять цену позиции _(п.5.12)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Provider/PositionUpdatePrice2` — Поменять цены нескольких позиций _(п.5.12.1)_

## Returns
- **GET** `https://www.catalog.stutzen.ru/api1c/Returns/return_requests?limit=100&get_messages=1&rrt_id=x1&getall=false` — Запросы на возврат _(п.4.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Returns/request_messages?rrm_id=x1` — Сообщения запроса _(п.4.1.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Returns/last_request_messages?minutes=x` — Последние сообщения _(п.4.1.2)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Returns/last_request_messages2?rmm_id=x` — Все сообщения с фильтром _(п.4.1.2.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Returns/set_status?rrt_id=x1&rrt_rss_id=x2&rrt_answer=x3` — Изменить статус возврата _(п.4.2)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Returns/request_messages_set_rrm_fl_show?rrm_id=x1&rrm_fl_show=x2` — Изменить статус сообщения _(п.4.3)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Returns/create_request_message?rrt_id=x1&rrm_author=x2&rrm_text=x3` — Создать сообщение _(п.4.4)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Returns/create_request_message2` — Создать сообщение (new) _(п.4.4.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Returns/return_position_to_stock?pst_id=x1` — Вернуть позицию на склад _(п.4.5)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Returns/CreateReturnRequest?pst_id=x1` — Создать запрос на возврат _(п.4.6)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Returns/CreateDocumentReturnRequest` — Создать документ возврата _(п.4.7)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Returns/return_requests?limit=100&get_messages=1&rrt_id=500` — Запросы на возврат - упрощенный вариант _(п.4.8)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Returns/SetRssId` — Изменить ид причины обращения в заявке на возврат. _(п.4.9)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Returns/setrrtdescription` — Изменить дополнительную информацию заявки на возврат. _(п.4.10)_

## Finance
- **GET** `https://www.catalog.stutzen.ru/api1c/Finance/lastminutes?min=x&pmk_id=g` — Поступление оплат за последние х минут _(п.1.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Finance/getallpayments?year=x&pmk_id=g` — Поступление всех оплат за год _(п.1.2)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Finance/getallpayments_period?DTStart=y&DTEnd=z&pmk_id=g` — Поступление оплат от всех клиентов за период _(п.1.3)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Finance/getallpaymentsproviders_period?DTStart=y&DTEnd=z` — Оплата поставщикам за период _(п.1.4)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Finance/create_client_payment?cst_id=14&external_num=внешний_номер&pmt_pmk_id=1&dcm_sum=111.5&comment=комментарий` — Создать оплату клиента _(п.1.5)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Finance/create_provider_payment?provider_id=425&external_num=внешний_номер&pmt_pmk_id=1&dcm_sum=111.5&comment=комментарий` — Создать оплату поставщика _(п.1.6)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Finance/payment` — Создать оплату (универсальный) _(п.1.7)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Finance/payment2` — Создать оплату (новый метод) _(п.1.7.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Finance/Debt` — Создать списание со счета _(п.1.7.2)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Finance/ProviderDebt` — Создать оплату поставщику (расчеты за заказы) _(п.1.7.3)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Finance/deletepayment` — Удалить оплату _(п.1.8)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Finance/getcursdollar` — Получить текущий курс доллара _(п.1.10)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Finance/setcursdollar?new_curs=x` — Задать курс доллара _(п.1.11)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Finance/GetUnpaidSales` — Неоплаченные реализации _(п.1.12)_

## Customers
- **GET** `https://www.catalog.stutzen.ru/api1c/Customers/getone?cst_id=x` — Получить клиента по ИД _(п.3.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Customers/getallcustomersinlastday?days=x` — Клиенты за последние дни _(п.3.2)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Customers/getallcustomers?limit=x&off_set=y` — Все клиенты _(п.3.3)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Customers/getallcustomershue` — Клиенты с отрицательным балансом _(п.3.4)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Customers/getbalanse?cst_id=x` — Баланс клиента _(п.3.5)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Customers/getbalanses` — Балансы нескольких клиентов _(п.3.5.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Customers/getallcustomers_shipments` — Клиенты для отгрузок _(п.3.6)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Customers/getallcustomerslastmodified?minutes=x` — Измененные клиенты _(п.3.7)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Customers/GetCategoryClients` — Категории клиентов _(п.3.8)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Customers/GetInvoicesDebts?dtStart=x1&dtStop=x2&latest=1000` — Дебиторская задолженность _(п.3.9)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Customers/UpdateCustomer` — Редактировать клиента _(п.3.10)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Customers/GetCustomerPayer?pyr_cst_id=262788` — Реквизиты организации _(п.3.11)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Customers/SetDebtIgnor?cst_id=0&cst_debt_ignor=true` — Разрешить игнорирование правил отгрузки _(п.3.12)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Customers/SetDebtIgnorAll` — Разрешить игнорирование для всех _(п.3.12.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Customers/WithdrawPayment?pst_id=x1` — Снять оплату с позиции _(п.3.14)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Customers/WithdrawPayments` — Снять оплаты с нескольких позиций _(п.3.14.1)_

## Order
- **POST** `https://www.catalog.stutzen.ru/api1c/Order/Create` — Создать заказ клиента _(п.6.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Order/Create2` — Создать заказ поставщика _(п.6.2)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Order/getorders?dtStart=x1&dtEnd=x2&last_minutes_modified=x3&positions=true` — Заказы за период _(п.6.3)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Order/getorders2?dtStart=x1&dtEnd=x2` — Заказы по измененным позициям _(п.6.3.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Order/GetOrdersFromLog?last_log_id=x1&positions=x2` — Заказы по журналу событий _(п.6.3.2)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Order/GetPositionsInOrder?ord_id=x1` — Позиции в заказе _(п.6.4)_

## ComplexRates
- **GET** `https://www.catalog.stutzen.ru/api1c/ComplexRates/getall` — Список правил _(п.7.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/ComplexRates/save` — Сохранить список правил (в разработке) _(п.7.2)_
- **POST** `https://www.catalog.stutzen.ru/api1c/ComplexRates/load` — Загрузить список правил (в разработке) _(п.7.3)_
- **POST** `https://www.catalog.stutzen.ru/api1c/ComplexRates/clear` — Очистить список правил (в разработке) _(п.7.4)_
- **POST** `https://www.catalog.stutzen.ru/api1c/ComplexRates/create` — Создать правило (на тестировании) _(п.7.5)_
- **POST** `https://www.catalog.stutzen.ru/api1c/ComplexRates/createlist` — Создать список правил (в разработке) _(п.7.6)_
- **POST** `https://www.catalog.stutzen.ru/api1c/ComplexRates/edit` — Редактировать правило (в тестировании) _(п.7.7)_
- **GET** `https://www.catalog.stutzen.ru/api1c/ComplexRates/getone` — Получить правило (в разработке) _(п.7.8)_
- **POST** `https://www.catalog.stutzen.ru/api1c/ComplexRates/delete` — Удалить правило (в разработке) _(п.7.9)_

## Pricelist
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/CopyProvidersPrices?providers_prices_id=2` — Статистика проценок _(п.8.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetPricelists` — Прайс-листы из Автопрайса _(п.9.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetPriceListSettings` — Настройки прайс-листов _(п.9.1.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Pricelist/SetCurrectPrice?providers_prices_id=x1&correct_price=x2&markup_id=x3&delivery_days=x4&max_days=x5&dlv_id=x6` — Задать наценку на прайс-лист _(п.9.2)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetPositions?pricelist_id=x1&part=x2` — Позиции прайс-листа _(п.9.3)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetPriceInfo?pricelist_id=x1` — Информация о прайс-листе _(п.9.4)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetCurrencies` — Курсы валют _(п.9.5)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetDeliveryConditions` — Способы доставки _(п.9.6)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Pricelist/EnablePriceList?pricelist_id=x1&enable=x2` — Включить/Выключить прайс-лист _(п.9.7)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetMarkups` — Список наценок _(п.9.8)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetProducers` — Список брендов _(п.9.9)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetProducer?prd_id=6590454` — Получить бренд _(п.9.9.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetProducerNames` — Синонимы брендов _(п.9.10)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetDetails?count=x1&mode=x2` — Справочник деталей _(п.9.11)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Pricelist/RunTaskPrice` — Выполнить прайс-задание _(п.9.12)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Pricelist/DeletePositionsInPrices?pst_state_id=x1&day=x2&Delete=x3` — Удалить позиции по статусу _(п.9.13)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetPriceListDelInfo?day=x1` — Просроченные прайс-листы _(п.9.14)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Pricelist/DeletePositionsInPriceRaw?pricelist_id=x1` — Удалить позиции прайс-листа _(п.9.15)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Pricelist/DeletePositionsInPriceRaw2?pricelist_ids=x1` — Удалить позиции нескольких прайс-листов _(п.9.15.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetTaskPrices` — Список прайс-заданий _(п.9.16)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetPriceFiles` — Список прайс-файлов _(п.9.17)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetPriceFiles` — Поместить скрипт в очередь _(п.9.18)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Pricelist/GetInsertingPrices` — Получить стек команд _(п.9.19)_

## Log
- **GET** `https://www.catalog.stutzen.ru/api1c/Log/GetLogs?log_lgt_id=x1&lastMinutes=30` — Логи за последние минуты _(п.10.2)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Log/GetLogs2?last_log_id=x1` — Логи по последнему ИД _(п.10.2.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Log/GetLogTypes` — Список прайс-заданий _(п.14.1)_

## City
- **GET** `https://www.catalog.stutzen.ru/api1c/City/GetCitys` — Список городов _(п.12.1)_

## Detail
- **GET** `https://www.catalog.stutzen.ru/api1c/Detail/GetDetails?limit=100` — Справочник деталей _(п.15.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Detail/GetDetail?detail_id=12441` — Получить деталь по ИД _(п.15.1.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Detail/EditDetail` — Изменить запись _(п.15.1.2)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Detail/DeleteDetails` — Удалить записи _(п.15.1.3)_

## ProducerNames
- **GET** `https://www.catalog.stutzen.ru/api1c/ProducerNames/GetProducerNames` — Имена производителей _(п.16.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/ProducerNames/GetProducerName?prd_id=353` — Синоним бренда _(п.16.1.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/ProducerNames/EditProducer` — Редактировать производителя _(п.17.1.2)_

## Producers
- **GET** `https://www.catalog.stutzen.ru/api1c/Producers/GetProducers` — Список производителей _(п.17.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Producers/GetProducer?prd_id=232323` — Получить производителя _(п.17.1.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/Producers/GetLastModifiedProducers?min=60` — Измененные производители _(п.17.1.1.1)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Producers/DeleteProducers` — Удалить производителей _(п.17.1.3)_
- **POST** `https://www.catalog.stutzen.ru/api1c/Producers/DeleteProducers2` — Удалить производителей и имена _(п.17.1.4)_

## Document
- **GET** `https://www.catalog.stutzen.ru/api1c/Document/List?startDate=x1&stopDate=x2&dcm_dct_id=x3` — Список документов _(п.18.1)_

## ComplexSearchReplace
- **GET** `https://www.catalog.stutzen.ru/api1c/ComplexSearchReplace/list` — Получить все замены направлений _(п.20.1)_
- **GET** `https://www.catalog.stutzen.ru/api1c/ComplexSearchReplace/getone?cre_id=1453` — Получить направление _(п.20.2)_
- **POST** `https://www.catalog.stutzen.ru/api1c/ComplexSearchReplace/create` — Создать замену направления _(п.20.3)_
- **POST** `https://www.catalog.stutzen.ru/api1c/ComplexSearchReplace/update` — Обновить замену направления _(п.20.4)_
- **POST** `https://www.catalog.stutzen.ru/api1c/ComplexSearchReplace/delete?cre_id=2082` — Удалить замену направления _(п.20.5)_
- **POST** `https://www.catalog.stutzen.ru/api1c/ComplexSearchReplace/createorupdate` — Создать или обновить замену направления _(п.20.6)_
