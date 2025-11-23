import { Router } from 'express';
import { register, login, logout, resetPassword } from '../controllers/auth.controller';

const router = Router();

router.post('/register', register);
router.post('/login', login);
router.post('/logout', logout);
router.post('/reset', resetPassword);

export default router;