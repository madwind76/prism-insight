"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Brain, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Clock, Target, BarChart3 } from "lucide-react"
import type { DashboardData } from "@/types/dashboard"

interface AIDecisionsPageProps {
  data: DashboardData
}

export function AIDecisionsPage({ data }: AIDecisionsPageProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("ko-KR", {
      style: "currency",
      currency: "KRW",
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString("ko-KR", { 
      year: "numeric",
      month: "long", 
      day: "numeric",
    })
  }

  const formatTime = (timeString: string) => {
    const [hours, minutes] = timeString.split(":")
    return `${hours}:${minutes}`
  }

  // holding_decisions를 날짜별로 그룹화
  const decisionsByDate = data.holding_decisions?.reduce((acc, decision) => {
    if (!acc[decision.decision_date]) {
      acc[decision.decision_date] = []
    }
    acc[decision.decision_date].push(decision)
    return acc
  }, {} as Record<string, typeof data.holding_decisions>) || {}

  const sortedDates = Object.keys(decisionsByDate).sort((a, b) => b.localeCompare(a))

  // holdings와 매칭하여 종목 정보 가져오기
  const getStockInfo = (ticker: string) => {
    return data.holdings?.find(h => h.ticker === ticker)
  }

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-lg bg-gradient-to-br from-purple-500/20 to-pink-500/20">
            <Brain className="w-6 h-6 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground">AI 보유 분석</h2>
            <p className="text-sm text-muted-foreground">보유 종목에 대한 AI의 일일 판단 기록</p>
          </div>
        </div>
        <Badge variant="outline" className="text-sm">
          총 {data.holding_decisions?.length || 0}건의 분석
        </Badge>
      </div>

      {/* 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-border/50">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-2">
              <CheckCircle className="w-5 h-5 text-success" />
              <span className="text-sm text-muted-foreground">총 분석 기록</span>
            </div>
            <p className="text-3xl font-bold text-foreground">
              {data.holding_decisions?.length || 0}건
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              모두 보유 유지 판단
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-2">
              <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              <span className="text-sm text-muted-foreground">조정 필요</span>
            </div>
            <p className="text-3xl font-bold text-amber-600 dark:text-amber-400">
              {data.holding_decisions?.filter(d => d.portfolio_adjustment_needed === 1).length || 0}건
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              포트폴리오 재조정 권고
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardContent className="p-6">
            <div className="flex items-center gap-3 mb-2">
              <BarChart3 className="w-5 h-5 text-chart-3" />
              <span className="text-sm text-muted-foreground">분석 종목 수</span>
            </div>
            <p className="text-3xl font-bold text-chart-3">
              {new Set(data.holding_decisions?.map(d => d.ticker)).size || 0}개
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              누적 종목 기준
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 일별 분석 내역 */}
      <div className="space-y-4">
        {sortedDates.map(date => (
          <Card key={date} className="border-border/50">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <Clock className="w-5 h-5 text-muted-foreground" />
                  {formatDate(date)}
                </CardTitle>
                <Badge variant="secondary">
                  {decisionsByDate[date].length}개 분석
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {decisionsByDate[date].map((decision) => {
                  const stock = getStockInfo(decision.ticker)
                  return (
                    <Card key={decision.id} className="border-border/30 bg-muted/20">
                      <CardContent className="p-6">
                        <div className="space-y-4">
                          {/* 종목 헤더 */}
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2">
                                <h3 className="text-lg font-bold text-foreground">
                                  {stock?.company_name || decision.ticker}
                                </h3>
                                <Badge variant="outline" className="text-xs">
                                  {decision.ticker}
                                </Badge>
                                <Badge className="bg-success/20 text-success border-success/30">
                                  <CheckCircle className="w-3 h-3 mr-1" />
                                  보유 유지
                                </Badge>
                              </div>
                              <p className="text-sm text-muted-foreground">
                                분석 시각: {formatTime(decision.decision_time)}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-sm text-muted-foreground mb-1">신뢰도</p>
                              <div className="flex items-center gap-2">
                                <div className="w-12 h-2 bg-muted rounded-full overflow-hidden">
                                  <div 
                                    className="h-full bg-gradient-to-r from-primary to-purple-600 rounded-full"
                                    style={{ width: `${(decision.confidence / 10) * 100}%` }}
                                  />
                                </div>
                                <span className="text-lg font-bold text-primary">
                                  {decision.confidence}/10
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* 현재 가격 정보 */}
                          {stock && (
                            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 p-4 rounded-lg bg-background border border-border/50">
                              <div>
                                <p className="text-xs text-muted-foreground mb-1">분석 시점 가격</p>
                                <p className="font-semibold text-foreground">{formatCurrency(decision.current_price)}</p>
                              </div>
                              <div>
                                <p className="text-xs text-muted-foreground mb-1">매수가</p>
                                <p className="font-semibold text-foreground">{formatCurrency(stock.buy_price || 0)}</p>
                              </div>
                              <div>
                                <p className="text-xs text-muted-foreground mb-1">목표가</p>
                                <p className="font-semibold text-success">{formatCurrency(stock.target_price || 0)}</p>
                              </div>
                              <div>
                                <p className="text-xs text-muted-foreground mb-1">손절가</p>
                                <p className="font-semibold text-destructive">{formatCurrency(stock.stop_loss || 0)}</p>
                              </div>
                              <div>
                                <p className="text-xs text-muted-foreground mb-1">수익률</p>
                                <p className={`font-semibold ${(stock.profit_rate || 0) >= 0 ? "text-success" : "text-destructive"}`}>
                                  {formatPercent(stock.profit_rate || 0)}
                                </p>
                              </div>
                            </div>
                          )}

                          {/* AI 판단 근거 */}
                          <div className="space-y-3">
                            <div className="p-4 rounded-lg bg-primary/10 border border-primary/20">
                              <div className="flex items-start gap-2 mb-2">
                                <Brain className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                                <p className="text-sm font-semibold text-primary">AI 판단 근거</p>
                              </div>
                              <p className="text-sm text-foreground leading-relaxed pl-6">
                                {decision.sell_reason}
                              </p>
                            </div>

                            {/* 분석 요약 */}
                            <div className="grid md:grid-cols-2 gap-3">
                              <div className="p-4 rounded-lg bg-muted/50 border border-border/30">
                                <p className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-2">
                                  <TrendingUp className="w-4 h-4" />
                                  기술적 추세
                                </p>
                                <p className="text-sm text-foreground">{decision.technical_trend}</p>
                              </div>
                              <div className="p-4 rounded-lg bg-muted/50 border border-border/30">
                                <p className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-2">
                                  <BarChart3 className="w-4 h-4" />
                                  거래량 분석
                                </p>
                                <p className="text-sm text-foreground">{decision.volume_analysis}</p>
                              </div>
                              <div className="p-4 rounded-lg bg-muted/50 border border-border/30">
                                <p className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-2">
                                  <Target className="w-4 h-4" />
                                  시장 영향
                                </p>
                                <p className="text-sm text-foreground">{decision.market_condition_impact}</p>
                              </div>
                              <div className="p-4 rounded-lg bg-muted/50 border border-border/30">
                                <p className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-2">
                                  <Clock className="w-4 h-4" />
                                  시간 요인
                                </p>
                                <p className="text-sm text-foreground">{decision.time_factor}</p>
                              </div>
                            </div>

                            {/* 포트폴리오 조정 */}
                            <div className={`p-4 rounded-lg border ${
                              decision.portfolio_adjustment_needed === 1
                                ? "bg-amber-500/10 border-amber-500/20"
                                : "bg-muted/50 border-border/30"
                            }`}>
                              <div className="flex items-start gap-2 mb-2">
                                {decision.portfolio_adjustment_needed === 1 ? (
                                  <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
                                ) : (
                                  <CheckCircle className="w-4 h-4 text-success mt-0.5 flex-shrink-0" />
                                )}
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <p className={`text-sm font-semibold ${
                                      decision.portfolio_adjustment_needed === 1
                                        ? "text-amber-600 dark:text-amber-400"
                                        : "text-success"
                                    }`}>
                                      {decision.portfolio_adjustment_needed === 1 
                                        ? "포트폴리오 조정 필요" 
                                        : "현재 전략 유지"}
                                    </p>
                                    {decision.adjustment_urgency && (
                                      <Badge 
                                        variant="outline" 
                                        className={
                                          decision.portfolio_adjustment_needed === 1
                                            ? "border-amber-500/50 text-amber-600 dark:text-amber-400 text-xs"
                                            : "border-success/50 text-success text-xs"
                                        }
                                      >
                                        긴급도: {decision.adjustment_urgency}
                                      </Badge>
                                    )}
                                  </div>
                                  <p className="text-sm text-foreground mb-3">{decision.adjustment_reason}</p>
                                  
                                  {/* 목표가/손절가 변경 정보 */}
                                  {(decision.new_target_price > 0 || decision.new_stop_loss > 0) && (
                                    <div className="grid grid-cols-2 gap-3 mt-3 pt-3 border-t border-border/30">
                                      {decision.new_target_price > 0 && (
                                        <div>
                                          <p className="text-xs text-muted-foreground mb-1">신규 목표가 이력</p>
                                          <div className="flex items-center gap-2">
                                            <p className="text-sm line-through text-muted-foreground">
                                              {formatCurrency(stock?.scenario?.target_price || 0)}
                                            </p>
                                            <TrendingUp className="w-3 h-3 text-success" />
                                            <p className="text-sm font-semibold text-success">
                                              {formatCurrency(decision.new_target_price)}
                                            </p>
                                          </div>
                                        </div>
                                      )}
                                      {decision.new_stop_loss > 0 && (
                                        <div>
                                          <p className="text-xs text-muted-foreground mb-1">신규 손절가 이력</p>
                                          <div className="flex items-center gap-2">
                                            <p className="text-sm line-through text-muted-foreground">
                                              {formatCurrency(stock?.scenario?.stop_loss || 0)}
                                            </p>
                                            <TrendingDown className="w-3 h-3 text-destructive" />
                                            <p className="text-sm font-semibold text-destructive">
                                              {formatCurrency(decision.new_stop_loss)}
                                            </p>
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {(!data.holding_decisions || data.holding_decisions.length === 0) && (
        <Card className="border-border/50">
          <CardContent className="p-12 text-center">
            <Brain className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-50" />
            <p className="text-muted-foreground">아직 AI 보유 분석 내역이 없습니다.</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
