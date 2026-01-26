import { useState, useEffect } from 'react'
import Loading from './Loading'
import ErrorMessage from './ErrorMessage'
import { apiFetch } from '../utils/api'
import { formatNumber } from '../utils/formatNumber'
import './PartnerBalance.css'
import { useLanguage } from '../contexts/LanguageContext'
import { languageService } from '../utils/language'

interface PartnerBalanceProps {
  telegramUserId: number
  partnerId: number
  startDate: string
  endDate: string
  botName: string | null
}

interface Firm {
  id: number
  name: string
  [key: string]: any
}

interface Currency {
  id: number
  name: string
  code_chr: string
  [key: string]: any
}

interface BalanceEntry {
  id: number
  date: number
  document_code: string
  document_id: number
  start_amount: number
  debit: number
  credit: number
  currency_amount: number
  exchange_rate: number
  currency: Currency
  firm: Firm
  document_type: {
    id: number
    name: string
  }
}

function PartnerBalance({ telegramUserId, partnerId, startDate, endDate, botName }: PartnerBalanceProps) {
  const [firms, setFirms] = useState<Firm[]>([])
  const [currencies, setCurrencies] = useState<Currency[]>([])
  const [selectedFirms, setSelectedFirms] = useState<number[]>([])
  const [selectedCurrencies, setSelectedCurrencies] = useState<number[]>([])
  const [balance, setBalance] = useState<BalanceEntry[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const { t } = useLanguage()
  // Get inverted labels for partner view
  const [isLoadingBalance, setIsLoadingBalance] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (botName) {
      fetchFirmsAndCurrencies()
    }
  }, [telegramUserId, botName])

  useEffect(() => {
    if (botName && selectedFirms.length > 0 && selectedCurrencies.length > 0) {
      fetchBalance()
    } else {
      setBalance([])
    }
  }, [selectedFirms, selectedCurrencies, startDate, endDate, telegramUserId, partnerId, botName])

  const fetchFirmsAndCurrencies = async () => {
    // SECURITY: bot_name is REQUIRED
    if (!botName) {
      setError(t('partner-balance.error.bot-name-required', 'Bot name is required. Please refresh the page.'))
      setIsLoading(false)
      return
    }
    
    setIsLoading(true)
    setError(null)

    try {
      const firmsUrl = new URL('/telegram-webapp/firms', window.location.origin)
      firmsUrl.searchParams.set('telegram_user_id', telegramUserId.toString())
      firmsUrl.searchParams.set('bot_name', botName) // REQUIRED
      
      const currenciesUrl = new URL('/telegram-webapp/currencies', window.location.origin)
      currenciesUrl.searchParams.set('telegram_user_id', telegramUserId.toString())
      currenciesUrl.searchParams.set('bot_name', botName) // REQUIRED
      
      const [firmsResponse, currenciesResponse] = await Promise.all([
        apiFetch(firmsUrl.pathname + firmsUrl.search),
        apiFetch(currenciesUrl.pathname + currenciesUrl.search)
      ])

      const firmsData = await firmsResponse.json()
      const currenciesData = await currenciesResponse.json()

      if (firmsData.ok) {
        setFirms(firmsData.firms || [])
      }
      if (currenciesData.ok) {
        setCurrencies(currenciesData.currencies || [])
      }
    } catch (err) {
      setError(t('partner-balance.error.load-firms-currencies', 'Error loading firms and currencies'))
    } finally {
      setIsLoading(false)
    }
  }

  const fetchBalance = async () => {
    // SECURITY: bot_name is REQUIRED
    if (!botName) {
      setError(t('partner-balance.error.bot-name-required', 'Bot name is required. Please refresh the page.'))
      setIsLoadingBalance(false)
      return
    }
    
    setIsLoadingBalance(true)
    setError(null)

    try {
      const firmIds = selectedFirms.join(',')
      const currencyIds = selectedCurrencies.join(',')

      const url = new URL('/telegram-webapp/partner-balance', window.location.origin)
      url.searchParams.set('telegram_user_id', telegramUserId.toString())
      url.searchParams.set('partner_id', partnerId.toString())
      url.searchParams.set('start_date', startDate)
      url.searchParams.set('end_date', endDate)
      url.searchParams.set('firm_ids', firmIds)
      url.searchParams.set('currency_ids', currencyIds)
      url.searchParams.set('bot_name', botName) // REQUIRED
      
      const response = await apiFetch(url.pathname + url.search)
      const data = await response.json()

      if (data.ok) {
        // Sort by date (latest to oldest) - backend already sorts, but ensure here too
        const sortedBalance = (data.balance || []).sort((a: BalanceEntry, b: BalanceEntry) => (b.date || 0) - (a.date || 0))
        setBalance(sortedBalance)
      } else {
        setError(t('partner-balance.error.fetch-balance', 'Failed to fetch balance'))
      }
    } catch (err) {
      setError(t('partner-balance.error.load-balance', 'Error loading balance'))
    } finally {
      setIsLoadingBalance(false)
    }
  }

  const toggleFirm = (firmId: number) => {
    setSelectedFirms(prev =>
      prev.includes(firmId)
        ? prev.filter(id => id !== firmId)
        : [...prev, firmId]
    )
  }

  const toggleCurrency = (currencyId: number) => {
    setSelectedCurrencies(prev =>
      prev.includes(currencyId)
        ? prev.filter(id => id !== currencyId)
        : [...prev, currencyId]
    )
  }

  const formatDate = (date: number) => {
    return new Date(date * 1000).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const calculateRemainder = (entry: BalanceEntry) => {
    // Invert the remainder: positive value for partner = negative balance
    const remainder = entry.start_amount + entry.debit - entry.credit
    return -remainder
  }

  const handleExport = async () => {
    if (selectedFirms.length === 0 || selectedCurrencies.length === 0) {
      setExportError(t('partner-balance.error.select-firm-currency', 'Выберите хотя бы одно предприятие и одну валюту'))
      return
    }

    setIsExporting(true)
    setExportError(null)

    try {
      const firmIds = selectedFirms.join(',')
      const currencyIds = selectedCurrencies.join(',')

      // SECURITY: bot_name is REQUIRED
      if (!botName) {
        setExportError(t('partner-balance.error.bot-name-required', 'Bot name is required. Please refresh the page.'))
        setIsExporting(false)
        return
      }
      
      const url = new URL('/telegram-webapp/partner-balance/export', window.location.origin)
      const currentLanguage = languageService.getCurrentLanguage()
      url.searchParams.set('telegram_user_id', telegramUserId.toString())
      url.searchParams.set('partner_id', partnerId.toString())
      url.searchParams.set('start_date', startDate)
      url.searchParams.set('end_date', endDate)
      url.searchParams.set('firm_ids', firmIds)
      url.searchParams.set('currency_ids', currencyIds)
      url.searchParams.set('bot_name', botName) // REQUIRED
      url.searchParams.set('lang_code', currentLanguage)
      
      const response = await apiFetch(url.pathname + url.search, {
        method: 'POST'
      })
      const data = await response.json()

      if (data.ok) {
        // Show success message
        const tg = window.Telegram?.WebApp
        if (tg) {
          tg.showAlert(t('partner-balance.export.success', 'Excel файл отправлен в ваш Telegram чат!'))
        } else {
          alert(t('partner-balance.export.success', 'Excel файл отправлен в ваш Telegram чат!'))
        }
      } else {
        setExportError(data.message || t('partner-balance.export.error', 'Ошибка при экспорте'))
      }
    } catch (err) {
      setExportError(t('partner-balance.export.error', 'Ошибка при отправке файла'))
    } finally {
      setIsExporting(false)
    }
  }

  if (isLoading) {
    return <Loading />
  }

  if (error) {
    return <ErrorMessage message={error} />
  }

  return (
    <div className="partner-balance">
      <div className="balance-header">
        <h2 className="balance-title">{t("partner-balance.header.title", "Баланс партнера")}</h2>
        {selectedFirms.length > 0 && selectedCurrencies.length > 0 && (
          <button
            className="export-balance-button"
            onClick={handleExport}
            disabled={isExporting}
          >
            {isExporting ? t('partner-balance.export.loading', '⏳ Отправка...') : t('partner-balance.export.download', '📥 Скачать Excel')}
          </button>
        )}
      </div>

      {exportError && (
        <div className="export-error">{exportError}</div>
      )}

      <div className="balance-filters">
        <div className="filter-section">
          <h3 className="filter-title">{t("partner-balance.filters.firms", "Предприятия")}</h3>
          <div className="checkbox-group">
            {firms.map(firm => (
              <label key={firm.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={selectedFirms.includes(firm.id)}
                  onChange={() => toggleFirm(firm.id)}
                />
                <span>{firm.name}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="filter-section">
          <h3 className="filter-title">{t("partner-balance.filters.currencies", "Валюты")}</h3>
          <div className="checkbox-group">
            {currencies.map(currency => (
              <label key={currency.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={selectedCurrencies.includes(currency.id)}
                  onChange={() => toggleCurrency(currency.id)}
                />
                <span>{currency.name} ({currency.code_chr})</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {selectedFirms.length === 0 || selectedCurrencies.length === 0 ? (
        <div className="balance-placeholder">
          {t("partner-balance.placeholder", "Выберите хотя бы одно предприятие и одну валюту для отображения баланса")}
        </div>
      ) : isLoadingBalance ? (
        <Loading />
      ) : balance.length === 0 ? (
        <div className="balance-empty">{t("partner-balance.empty", "Нет данных о балансе за выбранный период")}</div>
      ) : (
        <div className="balance-list">
          {balance.map(entry => {
            const remainder = calculateRemainder(entry)
            return (
              <div key={entry.id} className="balance-entry">
                <div className="balance-entry-header">
                  <span className="balance-document-code">{entry.document_code}</span>
                  <span className="balance-date">{formatDate(entry.date)}</span>
                </div>
                <div className="balance-entry-details">
                  <div className="balance-detail-row">
                    <span className="balance-label">{t("partner-balance.document-type", "Тип документа:")}</span>
                    {/* <span className="balance-value">{getPartnerDocumentTypeName(entry.document_type.name, "ru")}</span> */}
                    <span className="balance-value">{t(`partner-balance.document-type.${entry.document_type.id}`, entry.document_type.name)}</span>
                  </div>
                  <div className="balance-detail-row">
                    <span className="balance-label">{t("partner-balance.firm", "Предприятие:")}</span>
                    <span className="balance-value">{entry.firm.name}</span>
                  </div>
                  <div className="balance-detail-row">
                    <span className="balance-label">{t("partner-balance.currency", "Валюта:")}</span>
                    <span className="balance-value">{entry.currency.name} ({entry.currency.code_chr})</span>
                  </div>
                  <div className="balance-detail-row">
                    <span className="balance-label">{t("partner-balance.start-balance", "Начальный остаток:")}</span>
                    <span className="balance-value">
                      {formatNumber(-entry.start_amount)}
                    </span>
                  </div>
                  {/* Inverted for partner view: system credit -> partner debit */}
                  {entry.credit !== 0 && (
                    <div className="balance-detail-row">
                      <span className="balance-label">{t("partner-balance.debit", "Дебет")}:</span>
                      <span className="balance-value debit">
                        {formatNumber(entry.credit)}
                      </span>
                    </div>
                  )}
                  {/* Inverted for partner view: system debit -> partner credit */}
                  {entry.debit !== 0 && (
                    <div className="balance-detail-row">
                      <span className="balance-label">{t("partner-balance.credit", "Кредит")}:</span>
                      <span className="balance-value credit">
                        {formatNumber(-entry.debit)}
                      </span>
                    </div>
                  )}
                  <div className="balance-detail-row total">
                    <span className="balance-label">{t("partner-balance.remainder", "Остаток:")}</span>
                    <span className={`balance-value ${remainder >= 0 ? 'positive' : 'negative'}`}>
                      {formatNumber(remainder)}
                    </span>
                  </div>
                  {entry.exchange_rate !== 1 && (
                    <div className="balance-detail-row">
                      <span className="balance-label">{t("partner-balance.exchange-rate", "Курс обмена:")}</span>
                      <span className="balance-value">
                        {formatNumber(entry.exchange_rate, 4)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default PartnerBalance
