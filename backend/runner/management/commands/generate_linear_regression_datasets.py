from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from runner.models import Problem, ProblemData
from django.core.files.base import ContentFile
import pandas as pd
import numpy as np

class Command(BaseCommand):
    help = 'Generate synthetic datasets for linear regression problems'

    def handle(self, *args, **options):
        # Get the admin user
        try:
            admin_user = User.objects.get(username='admin')
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Admin user not found. Please create an admin user first.')
            )
            return
        
        # Get all problems created earlier
        problems = Problem.objects.filter(
            title__in=[
                'Simple Linear Regression: House Prices',
                'Multiple Linear Regression: Car Prices', 
                'Polynomial Regression: Temperature Prediction',
                'Ridge Regression: Medical Costs',
                'Lasso Regression: Sales Prediction'
            ]
        ).order_by('id')
        
        if len(problems) < 5:
            self.stdout.write(
                self.style.ERROR(f'Found only {len(problems)} problems, expected 5. Creating problems first...')
            )
            # Create the problems first
            from django.core.management import call_command
            call_command('create_linear_regression_problems')
            
            # Get the problems again
            problems = Problem.objects.filter(
                title__in=[
                    'Simple Linear Regression: House Prices',
                    'Multiple Linear Regression: Car Prices', 
                    'Polynomial Regression: Temperature Prediction',
                    'Ridge Regression: Medical Costs',
                    'Lasso Regression: Sales Prediction'
                ]
            ).order_by('id')
        
        # Generate datasets
        datasets = [
            ('house_prices', self.generate_house_prices_dataset()),
            ('car_prices', self.generate_car_prices_dataset()),
            ('temperature', self.generate_temperature_dataset()),
            ('medical_costs', self.generate_medical_costs_dataset()),
            ('advertising_sales', self.generate_sales_dataset())
        ]
        
        for i, (dataset_name, df) in enumerate(datasets):
            problem = problems[i]
            self.stdout.write(f'Creating dataset for problem: {problem.title}')
            
            # Split into train and test (80-20 split)
            n_train = int(len(df) * 0.8)
            train_df = df.iloc[:n_train].copy()
            test_df = df.iloc[n_train:].copy()
            
            # Remove target column from test set
            target_col = self.get_target_column(problem.title)
            test_df = test_df.drop(columns=[target_col])
            
            # Create sample submission from test set
            sample_submission_df = test_df[['id']].copy()
            sample_submission_df[target_col] = 0.0  # placeholder values
            
            # Save files to problem data
            problem_data = problem.data
            
            # Save train file
            train_csv = train_df.to_csv(index=False)
            problem_data.train_file.save(f'{dataset_name}_train.csv', ContentFile(train_csv.encode()))
            
            # Save test file
            test_csv = test_df.to_csv(index=False)
            problem_data.test_file.save(f'{dataset_name}_test.csv', ContentFile(test_csv.encode()))
            
            # Save sample submission file
            sample_csv = sample_submission_df.to_csv(index=False)
            problem_data.sample_submission_file.save(f'{dataset_name}_sample_submission.csv', ContentFile(sample_csv.encode()))
            
            problem_data.save()
            
            self.stdout.write(f'  - Saved train file with {len(train_df)} rows')
            self.stdout.write(f'  - Saved test file with {len(test_df)} rows')
            self.stdout.write(f'  - Saved sample submission file with {len(sample_submission_df)} rows')

    def generate_house_prices_dataset(self):
        """Generate synthetic house prices dataset"""
        np.random.seed(42)
        n_samples = 1000
        
        # Generate house sizes (in square meters)
        sizes = np.random.uniform(30, 300, n_samples)
        
        # Generate prices based on size with some noise
        # Base price: 100000 + size * 1500 + noise
        prices = 100000 + sizes * 1500 + np.random.normal(0, 20000, n_samples)
        prices = np.clip(prices, 50000, 2000000)  # reasonable price range
        
        df = pd.DataFrame({
            'id': range(n_samples),
            'size': sizes,
            'price': prices
        })
        
        return df

    def generate_car_prices_dataset(self):
        """Generate synthetic car prices dataset"""
        np.random.seed(42)
        n_samples = 1000
        
        # Generate features
        years = np.random.randint(2000, 2023, n_samples)
        mileage = np.random.uniform(0, 200000, n_samples)
        engine_size = np.random.uniform(1.0, 5.0, n_samples)
        fuel_types = np.random.choice(['gasoline', 'diesel', 'hybrid'], n_samples)
        
        # Convert categorical to numerical for modeling
        fuel_encoded = {'gasoline': 0, 'diesel': 1, 'hybrid': 2}
        fuel_numeric = [fuel_encoded[fuel] for fuel in fuel_types]
        
        # Generate prices based on features
        base_price = 20000
        year_factor = (years - 2000) * 500  # newer cars cost more
        mileage_factor = -mileage * 0.1     # more mileage = lower price
        engine_factor = engine_size * 3000  # larger engines cost more
        fuel_factor = np.array(fuel_numeric) * 2000  # hybrid premium
        
        prices = base_price + year_factor + mileage_factor + engine_factor + fuel_factor
        prices += np.random.normal(0, 3000, n_samples)  # add noise
        prices = np.clip(prices, 1000, 100000)  # reasonable price range
        
        df = pd.DataFrame({
            'id': range(n_samples),
            'year': years,
            'mileage': mileage,
            'engine_size': engine_size,
            'fuel_type': fuel_types,
            'price': prices
        })
        
        return df

    def generate_temperature_dataset(self):
        """Generate synthetic temperature dataset"""
        np.random.seed(42)
        n_samples = 365  # one for each day of the year
        
        # Generate day of year
        days = np.arange(1, n_samples + 1)
        
        # Model temperature as sinusoidal with seasonal variation
        # Average temp around 10°C with seasonal variation of ±15°C
        temperatures = 10 + 15 * np.sin(2 * np.pi * (days - 80) / 365)  # peak summer around day 80
        temperatures += np.random.normal(0, 3, n_samples)  # add daily variation
        
        df = pd.DataFrame({
            'id': days,
            'day_of_year': days,
            'temperature': temperatures
        })
        
        return df

    def generate_medical_costs_dataset(self):
        """Generate synthetic medical costs dataset"""
        np.random.seed(42)
        n_samples = 1338  # similar to the famous insurance dataset
        
        # Generate features
        ages = np.random.randint(18, 65, n_samples)
        bmi = np.random.normal(30, 6, n_samples)
        bmi = np.clip(bmi, 15, 50)  # realistic BMI range
        children = np.random.poisson(1.5, n_samples)  # average 1.5 children
        smokers = np.random.choice([0, 1], n_samples, p=[0.8, 0.2])  # 20% smokers
        regions = np.random.choice(['northeast', 'northwest', 'southeast', 'southwest'], n_samples)
        
        # Calculate charges based on factors
        base_charge = 1600  # base charge
        age_factor = (ages - 18) * 25  # older = more expensive
        bmi_factor = (bmi - 30) * 200  # higher BMI = more expensive
        child_factor = children * 400  # more children = more expensive
        smoker_factor = smokers * 20000  # smoking = much more expensive
        
        charges = base_charge + age_factor + bmi_factor + child_factor + smoker_factor
        charges += np.random.normal(0, 1000, n_samples)  # add individual variation
        charges = np.clip(charges, 1000, 60000)  # reasonable charge range
        
        df = pd.DataFrame({
            'id': range(n_samples),
            'age': ages,
            'bmi': bmi,
            'children': children,
            'smoker': ['yes' if s == 1 else 'no' for s in smokers],
            'region': regions,
            'charges': charges
        })
        
        return df

    def generate_sales_dataset(self):
        """Generate synthetic advertising sales dataset"""
        np.random.seed(42)
        n_samples = 200
        
        # Generate advertising budgets
        tv_budget = np.random.uniform(0, 300, n_samples)
        radio_budget = np.random.uniform(0, 50, n_samples)
        newspaper_budget = np.random.uniform(0, 100, n_samples)
        
        # Generate sales based on budgets
        # TV has highest impact, radio medium, newspaper low
        sales = 7 + 0.045 * tv_budget + 0.185 * radio_budget + 0.001 * newspaper_budget
        sales += np.random.normal(0, 3, n_samples)  # add noise
        sales = np.clip(sales, 0, 30)  # reasonable sales range
        
        df = pd.DataFrame({
            'id': range(n_samples),
            'tv_budget': tv_budget,
            'radio_budget': radio_budget,
            'newspaper_budget': newspaper_budget,
            'sales': sales
        })
        
        return df

    def get_target_column(self, title):
        """Extract target column name from problem title"""
        if 'House Prices' in title:
            return 'price'
        elif 'Car Prices' in title:
            return 'price'
        elif 'Temperature' in title:
            return 'temperature'
        elif 'Medical Costs' in title:
            return 'charges'
        elif 'Sales Prediction' in title:
            return 'sales'
        return 'target'