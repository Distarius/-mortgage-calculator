from flask import Flask, request, jsonify, render_template, send_file
import io
import pandas as pd

app = Flask(__name__)

# Функция расчета переплаты и общей суммы по ипотеке
# principal - сумма кредита, rate - годовая ставка в процентах, years - срок в годах

def calculate_mortgage(principal, rate, years, prepay=None, return_schedule=False):
    months = years * 12
    monthly_rate = rate / 100 / 12
    schedule = []
    p = principal
    m = months
    r = monthly_rate
    prepay_amount = 0
    prepay_period = 0
    prepay_type = 'reduce_payment'
    if prepay:
        try:
            prepay_amount = float(prepay.get('amount', 0))
            prepay_period = int(prepay.get('period', 0))
            prepay_type = prepay.get('type', 'reduce_payment')
        except Exception:
            prepay_amount = 0
            prepay_period = 0
            prepay_type = 'reduce_payment'
    if r == 0:
        monthly_payment = p / m
        total_payment = 0
        overpayment = 0
        paid = 0
        month = 0
        while p > 0.01 and month < m:
            pay = min(monthly_payment, p)
            prepay_this = 0
            if prepay and prepay_amount > 0 and prepay_period > 0 and (month % prepay_period == 0):
                prepay_this = min(prepay_amount, p - pay)
                pay += prepay_this
            p -= pay
            paid += pay
            schedule.append({
                'Месяц': month + 1,
                'Платёж': round(pay, 2),
                'Досрочный платёж': round(prepay_this, 2),
                'Остаток долга': round(max(p, 0), 2)
            })
            month += 1
        total_payment = paid
        overpayment = paid - principal
        result = {
            'monthly_payment': round(monthly_payment, 2),
            'total_payment': round(total_payment, 2),
            'overpayment': round(overpayment, 2)
        }
        if prepay and prepay_type == 'reduce_term':
            result['remaining_term'] = month
        if return_schedule:
            result['schedule'] = schedule
        return result
    else:
        # Аннуитет с досрочкой
        monthly_payment = p * (r * (1 + r) ** m) / ((1 + r) ** m - 1)
        paid = 0
        month = 0
        payments = []
        while p > 0.01 and month < 1000:
            interest = p * r
            pay = min(monthly_payment, p + interest)
            prepay_this = 0
            if prepay and prepay_amount > 0 and prepay_period > 0 and (month % prepay_period == 0):
                if prepay_type == 'reduce_payment':
                    p -= prepay_amount
                    # Пересчитываем платеж
                    left = m - month
                    if left > 0:
                        monthly_payment = p * (r * (1 + r) ** left) / ((1 + r) ** left - 1)
                else:  # reduce_term
                    prepay_this = min(prepay_amount, p + interest - pay)
                    pay += prepay_this
            p = p + interest - pay
            paid += pay
            payments.append(pay)
            schedule.append({
                'Месяц': month + 1,
                'Платёж': round(pay, 2),
                'Досрочный платёж': round(prepay_this, 2),
                'Остаток долга': round(max(p, 0), 2)
            })
            month += 1
            if p < 0.01:
                break
        total_payment = paid
        overpayment = paid - principal
        result = {
            'monthly_payment': round(payments[0], 2) if payments else 0,
            'total_payment': round(total_payment, 2),
            'overpayment': round(overpayment, 2)
        }
        if prepay and prepay_type == 'reduce_term':
            result['remaining_term'] = month
        if return_schedule:
            result['schedule'] = schedule
        return result

@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    data = request.get_json()
    principal = float(data.get('principal', 0))
    rate = float(data.get('rate', 0))
    years = int(data.get('years', 0))
    prepay = data.get('prepay')
    result = calculate_mortgage(principal, rate, years, prepay)
    return jsonify(result)

@app.route('/api/export_excel', methods=['POST'])
def export_excel():
    data = request.get_json()
    principal = float(data.get('principal', 0))
    rate = float(data.get('rate', 0))
    years = int(data.get('years', 0))
    prepay = data.get('prepay')
    result = calculate_mortgage(principal, rate, years, prepay, return_schedule=True)
    schedule = result.get('schedule', [])
    df = pd.DataFrame(schedule)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='График')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='mortgage_schedule.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    pass 