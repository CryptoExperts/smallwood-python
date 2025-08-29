import numpy as np

def format_theta(thetas, fnc):
    return [
        [fnc(subtheta) for subtheta in theta]
        for theta in thetas
    ]

class AbstractPACS:

    def get_field(self):
        raise NotImplementedError()

    def get_nb_wit_rows(self):
        raise NotImplementedError()
    
    def get_nb_wit_cols(self):
        raise NotImplementedError()
    
    def get_witness_size(self):
        return self.get_nb_wit_rows()*self.get_nb_wit_cols()

    def get_constraint_degree(self):
        raise NotImplementedError()
    
    def get_nb_parallel_constraints(self):
        raise NotImplementedError()
    
    def get_nb_aggregated_constraints(self):
        raise NotImplementedError()
    
    def get_theta(self):
        raise NotImplementedError()

    def evaluate_parallel_constraints(self, wit_evals, theta):
        raise NotImplementedError()
    
    def get_theta_(self):
        raise NotImplementedError()

    def evaluate_aggregated_constraints(self, wit_evals, theta):
        raise NotImplementedError()
    
    def test_witness(self, witness):
        nb_wit_rows = self.get_nb_wit_rows()
        nb_wit_cols = self.get_nb_wit_cols()
        nb_para_constraints = self.get_nb_parallel_constraints()
        nb_aggr_constraints = self.get_nb_aggregated_constraints()

        # Reshape as a matrix
        wit = np.array(witness).reshape((nb_wit_rows, nb_wit_cols))

        # Test Parallel Polynomial Constraints
        theta = self.get_theta()
        for k in range(nb_wit_cols):
            theta_k = format_theta(theta, fnc=lambda x: x[k])
            evals = self.evaluate_parallel_constraints(wit[:,k], theta_k)
            assert len(evals) == nb_para_constraints
            for eval in evals:
                if eval != 0:
                    print('PARA', k, eval)
                    return False

        # Test Aggregated Polynomial Constraints
        evals = [None]*nb_wit_cols
        theta_ = self.get_theta_()
        for k in range(nb_wit_cols):
            theta_k = format_theta(theta_, fnc=lambda x: x[k])
            evals[k] = self.evaluate_aggregated_constraints(wit[:,k], theta_k)
            #print('$', evals[k])
            #print(nb_aggr_constraints)
            assert len(evals[k]) == nb_aggr_constraints
        for j in range(nb_aggr_constraints):
            sum_eval = sum(evals[k][j] for k in range(nb_wit_cols))
            if sum_eval != 0:
                print('AGGR', j)
                print([evals[k][j] for k in range(nb_wit_cols)])
                return False
            
        return True
