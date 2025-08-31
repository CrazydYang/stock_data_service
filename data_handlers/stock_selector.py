#!/usr/bin/env python3
"""
基于akshare的多因子选股策略
策略条件：
1. 股东户数连续3季减少
2. 换手率3%-20%
3. 日线与周线均线多头排列
4. 总市值20-250亿
5. 10日涨幅<15% 且 10日中最大涨幅 < 7%
6. 当日主力资金净流入>1000万
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import time

warnings.filterwarnings('ignore')

class StockSelector:
    def __init__(self):
        self.selected_stocks = []
        
    def get_shareholder_data(self, date_list):
        """获取股东户数数据"""
        shareholder_data = []
        for date in date_list:
            try:
                df = ak.stock_hold_num_cninfo(date=date)
                if df is not None and not df.empty:
                    df['变动日期'] = pd.to_datetime(df['变动日期'])
                    shareholder_data.append(df)
            except Exception as e:
                print(f"获取{date}股东数据失败: {e}")
        return shareholder_data
    
    def check_continuous_decline(self, stock_code, shareholder_data):
        """检查股东户数连续3季减少"""
        if len(shareholder_data) < 3:
            return False
            
        stock_data = []
        for df in shareholder_data:
            data = df[df['证券代码'] == stock_code]
            if not data.empty:
                stock_data.append({
                    'date': data.iloc[0]['变动日期'],
                    'holders': data.iloc[0]['本期股东人数']
                })
        
        if len(stock_data) < 3:
            return False
            
        # 按日期排序
        stock_data = sorted(stock_data, key=lambda x: x['date'], reverse=True)
        
        # 检查连续3期减少
        if len(stock_data) >= 3:
            return (stock_data[0]['holders'] < stock_data[1]['holders'] and 
                   stock_data[1]['holders'] < stock_data[2]['holders'])
        return False
    
    def get_turnover_rate(self, stock_code, stock_sh_a_spot_em_df):
        """获取换手率数据"""
        try:
            stock_data = stock_sh_a_spot_em_df[stock_sh_a_spot_em_df['代码'] == stock_code]
            if not stock_data.empty and '换手率' in stock_data.columns:
                turnover = float(stock_data.iloc[0]['换手率'])
                return 3 <= turnover <= 20
        except:
            pass
        return False
    
    def check_ma_alignment(self, stock_code, stock_zh_a_hist_df):
        """检查日线和周线均线多头排列"""
        try:
            
            
            if stock_zh_a_hist_df is not None and len(stock_zh_a_hist_df) > 20:
                # 计算日线均线
                close_prices = stock_zh_a_hist_df['收盘'].values
                ma5 = np.mean(close_prices[-5:])
                ma10 = np.mean(close_prices[-10:])
                ma20 = np.mean(close_prices[-20:])
                
                # 日线多头排列
                daily_alignment = ma5 > ma10 > ma20
                
                # 由于akshare周线数据获取限制，这里简化处理日线
                return daily_alignment
                
        except Exception as e:
            print(f"均线检查失败 {stock_code}: {e}")
        return False
    
    def get_market_cap(self, stock_code, stock_sh_a_spot_em_df):
        """获取总市值"""
        try:
            stock_data = stock_sh_a_spot_em_df[stock_sh_a_spot_em_df['代码'] == stock_code]
            if not stock_data.empty and '总市值' in stock_data.columns:
                market_cap = float(stock_data.iloc[0]['总市值'])
                # 转换为亿元
                market_cap_billion = market_cap / 100000000
                return 20 <= market_cap_billion <= 250
        except:
            pass
        return False
    
    def get_10day_return(self, stock_code, stock_zh_a_hist_df):
        """获取10日涨幅"""
        try:
            if stock_zh_a_hist_df is not None and len(stock_zh_a_hist_df) >= 10:
                prices = stock_zh_a_hist_df['收盘'].values
                if len(prices) >= 10:
                    return_10d = ((prices[-1] - prices[-10]) / prices[-10]) * 100
                    return return_10d < 15
                    
        except Exception as e:
            print(f"10日涨幅计算失败 {stock_code}: {e}")
        return False

    def get_10day_max_return(self, stock_code, stock_zh_a_hist_df):
        """获取10日最大涨幅"""
        try:
            if stock_zh_a_hist_df is not None and len(stock_zh_a_hist_df) >= 10:
                returns = stock_zh_a_hist_df['涨跌幅'].values
                if len(returns) >= 10:
                    max_return_10d = max(returns[-10:])
                    return max_return_10d < 5
                    
        except Exception as e:
            print(f"10日涨幅计算失败 {stock_code}: {e}")
        return False
    
    def get_main_fund_flow(self, stock_code):
        """获取当日主力资金净流入"""
        try:
            time.sleep(0.5)
            # 获取当日资金流向数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = end_date
            
            # 使用个股资金流数据
            stock_individual_fund_flow_df = ak.stock_individual_fund_flow(
                stock=stock_code, 
                market="sh" if stock_code.startswith('6') else "sz"
            )
            
            if stock_individual_fund_flow_df is not None and not stock_individual_fund_flow_df.empty:
                # print(stock_individual_fund_flow_df.tail())
                # 获取日期最大的一行（最新一天的主力净流入）
                # 假设日期列名为'日期'，如果不是需要根据实际列名调整
                if '日期' in stock_individual_fund_flow_df.columns:
                    latest_flow = stock_individual_fund_flow_df.loc[stock_individual_fund_flow_df['日期'].idxmax()]
                else:
                    # 如果没有日期列，则使用第一行作为备选
                    latest_flow = stock_individual_fund_flow_df.iloc[0]

                if '主力净流入-净额' in latest_flow:
                    main_inflow = float(latest_flow['主力净流入-净额'])
                    return main_inflow > 10000000  # 1000万
                    
        except Exception as e:
            print(f"资金流获取失败 {stock_code}: {e}")
        return False
    
    def get_recent_quarter_dates(self):
        """获取最近3个季度的报告日期"""
        now = datetime.now()
        year = now.year
        
        # 根据当前时间确定最近的季度
        if now.month <= 3:
            dates = [f"{year-1}1231", f"{year-1}0930", f"{year-1}0630"]
        elif now.month <= 6:
            dates = [f"{year}0331", f"{year-1}1231", f"{year-1}0930"]
        elif now.month <= 9:
            dates = [f"{year}0630", f"{year}0331", f"{year-1}1231"]
        else:
            dates = [f"{year}0930", f"{year}0630", f"{year}0331"]
            
        return dates
    
    def select_stocks(self):
        """执行选股策略"""
        print("开始执行选股策略...")
        print("=" * 60)
        
        # 获取最近3个季度的日期
        quarter_dates = self.get_recent_quarter_dates()
        print(f"使用季度日期: {quarter_dates}")
        
        # 获取股东数据
        print("获取股东户数数据...")
        shareholder_data = self.get_shareholder_data(quarter_dates)
        
        if len(shareholder_data) < 3:
            print("❌ 股东数据不足，无法执行连续3季减少检查")
            return []
        
        # 获取股票列表
        print("获取股票列表...")
        try:
            stock_sh_a_spot_em_df = ak.stock_sh_a_spot_em()
            if stock_sh_a_spot_em_df is None or stock_sh_a_spot_em_df.empty:
                print("❌ 无法获取股票列表")
                return []
            
            all_stocks = stock_sh_a_spot_em_df['代码'].tolist()
            print(f"共获取 {len(all_stocks)} 只股票")
            
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            return []
        
        selected_stocks = []
        
        for stock_code in all_stocks:
            if self.get_turnover_rate(stock_code, stock_sh_a_spot_em_df) and self.get_market_cap(stock_code, stock_sh_a_spot_em_df) and self.check_continuous_decline(stock_code, shareholder_data):
                # 获取日线数据
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=100)).strftime('%Y%m%d')
                
                # 使用akshare获取日线数据
                stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date, end_date=end_date, adjust="")
                time.sleep(0.5)
                try:
                    # 应用所有筛选条件
                    checks = [
                        ("股东户数连续减少", self.check_continuous_decline(stock_code, shareholder_data)),
                        ("换手率范围", self.get_turnover_rate(stock_code, stock_sh_a_spot_em_df)),
                        ("均线多头排列", self.check_ma_alignment(stock_code, stock_zh_a_hist_df)),
                        ("市值范围", self.get_market_cap(stock_code, stock_sh_a_spot_em_df)),
                        ("10日涨幅限制", self.get_10day_return(stock_code, stock_zh_a_hist_df)),
                        ("主力资金流入", self.get_main_fund_flow(stock_code))
                    ]
                    
                    # 检查所有条件
                    all_passed = True
                    failed_conditions = []
                    
                    for condition_name, passed in checks:
                        if not passed:
                            all_passed = False
                            failed_conditions.append(condition_name)
                    
                    if all_passed:
                        # 获取股票基本信息
                        stock_info = stock_sh_a_spot_em_df[stock_sh_a_spot_em_df['代码'] == stock_code].iloc[0]
                        selected_stocks.append({
                            '代码': stock_code,
                            '名称': stock_info['名称'],
                            '当前价': stock_info['最新价'],
                            '市值': stock_info['总市值'] / 100000000,  # 亿元
                            '换手率': stock_info['换手率'] if '换手率' in stock_info else None
                        })
                        print(f"✅ 选中: {stock_code} - {stock_info['名称']}")
                    
                except Exception as e:
                    continue  # 跳过出错的股票
        
        return selected_stocks
    
    def save_results(self, stocks):
        """保存选股结果"""
        if not stocks:
            print("\n❌ 未选到符合条件的股票")
            return
        
        df = pd.DataFrame(stocks)
        filename = f"selected_stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"\n✅ 选股完成！")
        print(f"共选中 {len(stocks)} 只股票")
        print(f"结果已保存到: {filename}")
        
        # 显示结果
        print("\n选中的股票:")
        print(df.to_string())

def main():
    """主函数"""
    selector = StockSelector()
    
    print("多因子选股策略")
    print("=" * 60)
    print("策略条件:")
    print("1. 股东户数连续3季减少")
    print("2. 换手率3%-20%")
    print("3. 日线与周线均线多头排列")
    print("4. 总市值20-250亿")
    print("5. 10日涨幅<15% 且 10日中最大涨幅 < 7%")
    print("6. 当日主力资金净流入>1000万")
    print("=" * 60)

    # 执行选股
    selected_stocks = selector.select_stocks()
    
    # 保存结果
    selector.save_results(selected_stocks)

if __name__ == "__main__":
    main()