"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, TrendingDown } from "lucide-react"
import type { Holding } from "@/types/dashboard"

interface HoldingsTableProps {
  holdings: Holding[]
  onStockClick: (stock: Holding) => void
  title?: string
  isRealTrading?: boolean
}

export function HoldingsTable({ holdings, onStockClick, title = "보유 종목", isRealTrading = false }: HoldingsTableProps) {
  const formatCurrency = (value: number | undefined) => {
    if (value === undefined || value === null) return "₩0"
    return new Intl.NumberFormat("ko-KR", {
      style: "currency",
      currency: "KRW",
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatPercent = (value: number | undefined) => {
    if (value === undefined || value === null) return "0.00%"
    return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`
  }

  const formatWeight = (value: number | undefined) => {
    if (value === undefined || value === null) return "-"
    return `${value.toFixed(2)}%`
  }

  return (
    <Card className={`border-border/50 ${isRealTrading ? 'border-blue-500/30 bg-gradient-to-br from-blue-50/50 to-transparent dark:from-blue-950/20' : ''}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-lg font-semibold">{title}</CardTitle>
            {isRealTrading ? (
              <div className="flex items-center gap-2">
                <Badge variant="default" className="bg-gradient-to-r from-blue-600 to-indigo-600">
                  실전투자
                </Badge>
                <Badge variant="outline" className="border-blue-500/50 text-blue-600 dark:text-blue-400">
                  Season 2
                </Badge>
              </div>
            ) : (
              <Badge variant="outline" className="border-purple-500/50 text-purple-600 dark:text-purple-400">
                AI 시뮬레이션
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent border-border/50">
                <TableHead className="font-semibold">종목명</TableHead>
                {!isRealTrading && <TableHead className="font-semibold">섹터</TableHead>}
                {isRealTrading ? (
                  <>
                    <TableHead className="text-right font-semibold">수량</TableHead>
                    <TableHead className="text-right font-semibold">평균단가</TableHead>
                    <TableHead className="text-right font-semibold">현재가</TableHead>
                    <TableHead className="text-right font-semibold">평가금액</TableHead>
                    <TableHead className="text-right font-semibold">평가손익</TableHead>
                    <TableHead className="text-right font-semibold">수익률</TableHead>
                    <TableHead className="text-right font-semibold">비중</TableHead>
                  </>
                ) : (
                  <>
                    <TableHead className="text-right font-semibold">매수가</TableHead>
                    <TableHead className="text-right font-semibold">현재가</TableHead>
                    <TableHead className="text-right font-semibold">목표가</TableHead>
                    <TableHead className="text-right font-semibold">손절가</TableHead>
                    <TableHead className="text-right font-semibold">수익률</TableHead>
                    <TableHead className="text-right font-semibold">보유일</TableHead>
                    <TableHead className="text-right font-semibold">기간</TableHead>
                  </>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {holdings.map((holding) => {
                const stockName = holding.company_name || holding.name || "알 수 없음"
                const buyPrice = holding.buy_price || holding.avg_price || 0
                
                return (
                  <TableRow
                    key={holding.ticker}
                    className="cursor-pointer hover:bg-muted/50 transition-colors border-border/30"
                    onClick={() => onStockClick(holding)}
                  >
                    <TableCell>
                      <div>
                        <p className="font-medium text-foreground">{stockName}</p>
                        <p className="text-xs text-muted-foreground">{holding.ticker}</p>
                      </div>
                    </TableCell>
                    
                    {!isRealTrading && (
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {holding.sector}
                        </Badge>
                      </TableCell>
                    )}
                    
                    {isRealTrading ? (
                      <>
                        <TableCell className="text-right font-medium">
                          {(holding.quantity || 0).toLocaleString()}주
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {formatCurrency(holding.avg_price)}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatCurrency(holding.current_price)}
                        </TableCell>
                        <TableCell className="text-right font-semibold">
                          {formatCurrency(holding.value)}
                        </TableCell>
                        <TableCell className="text-right">
                          <span className={`font-semibold ${(holding.profit || 0) >= 0 ? "text-success" : "text-destructive"}`}>
                            {formatCurrency(holding.profit)}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            {(holding.profit_rate || 0) >= 0 ? (
                              <TrendingUp className="w-3 h-3 text-success" />
                            ) : (
                              <TrendingDown className="w-3 h-3 text-destructive" />
                            )}
                            <span className={`font-semibold ${(holding.profit_rate || 0) >= 0 ? "text-success" : "text-destructive"}`}>
                              {formatPercent(holding.profit_rate)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {formatWeight(holding.weight)}
                        </TableCell>
                      </>
                    ) : (
                      <>
                        <TableCell className="text-right text-muted-foreground">
                          {formatCurrency(buyPrice)}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {formatCurrency(holding.current_price)}
                        </TableCell>
                        <TableCell className="text-right text-success">
                          {formatCurrency(holding.target_price)}
                        </TableCell>
                        <TableCell className="text-right text-destructive">
                          {formatCurrency(holding.stop_loss)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            {(holding.profit_rate || 0) >= 0 ? (
                              <TrendingUp className="w-3 h-3 text-success" />
                            ) : (
                              <TrendingDown className="w-3 h-3 text-destructive" />
                            )}
                            <span className={`font-semibold ${(holding.profit_rate || 0) >= 0 ? "text-success" : "text-destructive"}`}>
                              {formatPercent(holding.profit_rate)}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {holding.holding_days || 0}일
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge variant={holding.investment_period === "단기" ? "secondary" : "outline"} className="text-xs">
                            {holding.investment_period || "-"}
                          </Badge>
                        </TableCell>
                      </>
                    )}
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
