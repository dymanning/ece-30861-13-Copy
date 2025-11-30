import { Router } from 'express';
import {
	register,
	login,
	logout,
	resetPassword,
	authenticate,
} from '../controllers/auth.controller';

const router = Router();

router.post('/register', register);
router.post('/login', login);
router.post('/logout', logout);
router.post('/reset', resetPassword);

// OpenAPI spec: PUT /authenticate
router.put('/authenticate', authenticate);

export default router;
